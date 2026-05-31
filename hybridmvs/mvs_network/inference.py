"""
Deep learning MVS inference pipeline.

Handles model loading, data preprocessing, depth map inference,
and post-processing for the hybrid reconstruction pipeline.
"""

import os
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import torch
import torch.nn.functional as F

from .mvsnet import MVSNet
from .cas_mvsnet import CasMVSNet

logger = logging.getLogger(__name__)


@dataclass
class MVSConfig:
    """Configuration for MVS inference."""
    model_type: str = "casmvsnet"        # "mvsnet" or "casmvsnet"
    num_views: int = 3                    # Number of input views (1 ref + N-1 src)
    min_depth: float = 0.5
    max_depth: float = 100.0
    depth_planes: List[int] = None        # Depth planes per stage for CasMVSNet
    img_height: int = 512
    img_width: int = 640
    checkpoint_path: Optional[str] = None # Pretrained model weights
    device: str = "cuda"


class MVSInference:
    """
    Inference engine for deep learning MVS depth estimation.

    Usage:
        infer = MVSInference(MVSConfig())
        depth_maps, confidence = infer.run(images, intrinsics, extrinsics)
    """

    def __init__(self, config: MVSConfig):
        self.config = config
        self.device = torch.device(config.device if torch.cuda.is_available() else "cpu")

        if config.depth_planes is None:
            config.depth_planes = [128, 64, 48]

        self.model = self._build_model()
        if config.checkpoint_path and os.path.isfile(config.checkpoint_path):
            self._load_checkpoint(config.checkpoint_path)

        self.model.to(self.device)
        self.model.eval()

        logger.info(f"MVSInference initialized: {config.model_type} on {self.device}")

    def _build_model(self) -> torch.nn.Module:
        """Build the MVS network."""
        if self.config.model_type == "mvsnet":
            return MVSNet(
                base_channels=8,
                feat_channels=32,
                depth_planes=192,
                min_depth=self.config.min_depth,
                max_depth=self.config.max_depth,
                mode="eval",
            )
        elif self.config.model_type == "casmvsnet":
            return CasMVSNet(
                base_channels=8,
                feat_channels=32,
                depth_planes=self.config.depth_planes,
                min_depth=self.config.min_depth,
                max_depth=self.config.max_depth,
            )
        else:
            raise ValueError(f"Unknown model type: {self.config.model_type}")

    def _load_checkpoint(self, path: str) -> None:
        """Load pretrained model weights."""
        logger.info(f"Loading pretrained weights from: {path}")
        state_dict = torch.load(path, map_location="cpu", weights_only=True)

        # Handle wrapped checkpoints
        if "model" in state_dict:
            state_dict = state_dict["model"]
        if "state_dict" in state_dict:
            state_dict = state_dict["state_dict"]

        # Remove "module." prefix from DataParallel
        new_state = {}
        for k, v in state_dict.items():
            k = k.replace("module.", "")
            new_state[k] = v

        missing, unexpected = self.model.load_state_dict(new_state, strict=False)
        if missing:
            logger.warning(f"Missing keys in checkpoint: {len(missing)} keys")
        if unexpected:
            logger.debug(f"Unexpected keys in checkpoint: {len(unexpected)} keys")

    def preprocess_images(
        self,
        images: List[np.ndarray],
        intrinsics: List[np.ndarray],
        extrinsics: List[np.ndarray],
        ref_idx: int = 0,
        depth_min: Optional[float] = None,
        depth_max: Optional[float] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Prepare input tensors for the MVS network.

        Args:
            images: List of [H, W, 3] uint8 images.
            intrinsics: List of [3, 3] camera intrinsic matrices.
            extrinsics: List of [4, 4] camera-to-world matrices.
            ref_idx: Index of the reference image.
            depth_min, depth_max: Depth range for the scene.

        Returns:
            Dict with 'imgs', 'intrinsics', 'extrinsics', 'depth_min', 'depth_max'.
        """
        cfg = self.config
        target_h, target_w = cfg.img_height, cfg.img_width
        N = min(len(images), cfg.num_views)

        # Select views centered on reference
        indices = [ref_idx]
        src_indices = [i for i in range(len(images)) if i != ref_idx]
        indices.extend(src_indices[:N - 1])
        N = len(indices)  # may be fewer than requested

        imgs_tensor = torch.zeros(N, 3, target_h, target_w, dtype=torch.float32)
        K_tensor = torch.zeros(N, 3, 3, dtype=torch.float32)
        E_tensor = torch.zeros(N, 4, 4, dtype=torch.float32)

        rel_scale_h = target_h / images[0].shape[0]
        rel_scale_w = target_w / images[0].shape[1]

        for i, idx in enumerate(indices):
            img = images[idx]
            K = intrinsics[idx].copy()
            E = extrinsics[idx]

            # Resize image
            img_t = torch.from_numpy(img).permute(2, 0, 1).float()  # [3, H, W]
            img_t = F.interpolate(img_t.unsqueeze(0), size=(target_h, target_w),
                                  mode='bilinear', align_corners=False).squeeze(0)
            # Normalize: [0,255] → [0,1] → ImageNet standardization
            img_t = img_t / 255.0
            mean = torch.tensor([0.485, 0.456, 0.406], device=img_t.device).view(3, 1, 1)
            std = torch.tensor([0.229, 0.224, 0.225], device=img_t.device).view(3, 1, 1)
            img_t = (img_t - mean) / std
            imgs_tensor[i] = img_t

            # Scale intrinsics to target resolution
            K[0, 0] *= rel_scale_w  # fx
            K[1, 1] *= rel_scale_h  # fy
            K[0, 2] *= rel_scale_w  # cx
            K[1, 2] *= rel_scale_h  # cy
            K_tensor[i] = torch.from_numpy(K).float()
            E_tensor[i] = torch.from_numpy(E).float()

        batch = {
            'imgs': imgs_tensor.unsqueeze(0),              # [1, N, 3, H, W]
            'intrinsics': K_tensor.unsqueeze(0),            # [1, N, 3, 3]
            'extrinsics': E_tensor.unsqueeze(0),            # [1, N, 4, 4]
        }

        if depth_min is not None:
            batch['depth_min'] = torch.tensor([depth_min], dtype=torch.float32)
        if depth_max is not None:
            batch['depth_max'] = torch.tensor([depth_max], dtype=torch.float32)

        return batch

    @torch.no_grad()
    def run(
        self,
        images: List[np.ndarray],
        intrinsics: List[np.ndarray],
        extrinsics: List[np.ndarray],
        ref_idx: int = 0,
        depth_min: Optional[float] = None,
        depth_max: Optional[float] = None,
        original_size: Optional[Tuple[int, int]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Run depth estimation inference.

        Args:
            images: List of [H, W, 3] uint8 images.
            intrinsics: List of [3, 3] intrinsic matrices.
            extrinsics: List of [4, 4] camera-to-world matrices.
            ref_idx: Index of reference image within the list.
            depth_min: Min scene depth.
            depth_max: Max scene depth.
            original_size: (H, W) to upsample output depth map to.

        Returns:
            depth_map: [H, W] float32 depth values.
            confidence: [H, W] float32 confidence scores in [0, 1].
        """
        self.model.eval()

        batch = self.preprocess_images(
            images, intrinsics, extrinsics, ref_idx,
            depth_min, depth_max,
        )

        imgs = batch['imgs'].to(self.device)
        K = batch['intrinsics'].to(self.device)
        E = batch['extrinsics'].to(self.device)

        kwargs = {}
        if 'depth_min' in batch:
            kwargs['depth_min'] = batch['depth_min'].to(self.device)
        if 'depth_max' in batch:
            kwargs['depth_max'] = batch['depth_max'].to(self.device)

        output = self.model(imgs, K, E, **kwargs)

        depth = output['depth'].squeeze(0).squeeze(0)  # [H, W]
        prob_vol = output['prob_volume'].squeeze(0)     # [1, D, H, W]
        depth_vals = output['depth_values'].squeeze(0)  # [D] or [D, H, W]

        # Compute confidence.
        # If cascade provided stage 2 prob (global depth range), use that —
        # it gives meaningful confidence. Otherwise use entropy on current prob.
        prob_s2 = output.get('prob_volume_stage2')
        if prob_s2 is not None:
            # Stage 2: global depth range, 128 planes at 1/4 resolution
            prob_s2 = prob_s2.squeeze(0).squeeze(0)  # [D2, H/4, W/4]
            H_full, W_full = depth.shape
            prob_s2_up = F.interpolate(
                prob_s2.unsqueeze(0), size=(H_full, W_full),
                mode='bilinear', align_corners=False,
            ).squeeze(0)  # [D2, H, W]
            # Entropy-based confidence on global-range distribution
            D2 = prob_s2_up.shape[0]
            entropy = -(prob_s2_up * torch.log(prob_s2_up + 1e-8)).sum(dim=0)  # [H, W]
            confidence = 1.0 - entropy / np.log(D2)
        elif depth_vals.ndim == 3:
            # Per-pixel depth (fallback), use entropy
            prob = prob_vol.squeeze(0)  # [D, H, W]
            D = prob.shape[0]
            entropy = -(prob * torch.log(prob + 1e-8)).sum(dim=0)
            confidence = 1.0 - entropy / np.log(D)
        else:
            # Global depth [D], use entropy
            prob = prob_vol.squeeze(0)  # [D, H, W]
            D = prob.shape[0]
            entropy = -(prob * torch.log(prob + 1e-8)).sum(dim=0)
            confidence = 1.0 - entropy / np.log(D)

        # Convert to numpy
        depth_np = depth.cpu().numpy()
        conf_np = confidence.cpu().numpy()

        # Upsample to original size if needed
        if original_size is not None:
            h_orig, w_orig = original_size
            depth_t = torch.from_numpy(depth_np).unsqueeze(0).unsqueeze(0)
            conf_t = torch.from_numpy(conf_np).unsqueeze(0).unsqueeze(0)
            depth_np = F.interpolate(depth_t, size=(h_orig, w_orig),
                                     mode='bilinear', align_corners=False
                                     ).squeeze().numpy()
            conf_np = F.interpolate(conf_t, size=(h_orig, w_orig),
                                    mode='bilinear', align_corners=False
                                    ).squeeze().numpy()

        return depth_np.astype(np.float32), conf_np.astype(np.float32)

    def run_all_views(
        self,
        images: List[np.ndarray],
        intrinsics: List[np.ndarray],
        extrinsics: List[np.ndarray],
        depth_min: Optional[float] = None,
        depth_max: Optional[float] = None,
    ) -> List[Dict[str, np.ndarray]]:
        """
        Run depth estimation for all views as reference.

        Returns:
            List of dicts with keys 'depth', 'confidence', 'image_name' for each view.
        """
        results = []
        orig_h, orig_w = images[0].shape[:2]

        for i in range(len(images)):
            logger.info(f"Processing view {i + 1}/{len(images)}")
            depth, conf = self.run(
                images, intrinsics, extrinsics,
                ref_idx=i,
                depth_min=depth_min,
                depth_max=depth_max,
                original_size=(orig_h, orig_w),
            )
            results.append({
                'depth': depth,
                'confidence': conf,
                'image_index': i,
            })

        return results
