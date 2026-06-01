"""
Adapter: official PatchMatchNet → MVSInference.run() interface.
Handles multi-scale image generation, proj_matrix construction,
checkpoint loading with 'module.' prefix stripping.
"""
import numpy as np
import torch
import torch.nn.functional as F
from typing import List, Tuple, Optional

from hybridmvs.PatchmatchNet.net import PatchmatchNet


class PatchMatchNetInference:
    """Thin wrapper matching MVSInference.run() signature."""

    def __init__(self, checkpoint_path: str, device: str = "cuda",
                 patchmatch_iteration=(1, 2, 2),
                 patchmatch_num_sample=(8, 8, 16),
                 propagate_neighbors=(0, 8, 16),
                 evaluate_neighbors=(9, 9, 9),
                 patchmatch_interval_scale=(0.005, 0.0125, 0.025),
                 propagation_range=(6, 4, 2)):
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")

        self.model = PatchmatchNet(
            patchmatch_interval_scale=list(patchmatch_interval_scale),
            propagation_range=list(propagation_range),
            patchmatch_iteration=list(patchmatch_iteration),
            patchmatch_num_sample=list(patchmatch_num_sample),
            propagate_neighbors=list(propagate_neighbors),
            evaluate_neighbors=list(evaluate_neighbors),
        )

        if checkpoint_path:
            self._load_checkpoint(checkpoint_path)

        self.model.to(self.device)
        self.model.eval()

    def _load_checkpoint(self, path: str):
        ckpt = torch.load(path, map_location="cpu", weights_only=True)
        state = ckpt.get("model", ckpt.get("state_dict", ckpt))

        # Strip 'module.' prefix (from DataParallel/DDP)
        new_state = {}
        for k, v in state.items():
            if k.startswith("module."):
                k = k[7:]
            new_state[k] = v

        missing, unexpected = self.model.load_state_dict(new_state, strict=False)
        if missing:
            print(f"[PatchMatchNet] Missing keys: {len(missing)}")
        if unexpected:
            print(f"[PatchMatchNet] Unexpected keys: {len(unexpected)}")

    @staticmethod
    def _build_proj_matrix(K: np.ndarray, E_c2w: np.ndarray, H: int, W: int,
                           scale_h: float = 1.0, scale_w: float = 1.0) -> np.ndarray:
        """Build 4x4 projection matrix P = K' @ W2C for a given scale.
        K is the original 3x3 intrinsic, E_c2w is 4x4 camera-to-world.
        K' is K scaled by (scale_w, scale_h).
        W2C = inv(E_c2w).
        Returns 4x4 matrix.
        """
        K_scaled = K.copy()
        K_scaled[0, 0] *= scale_w
        K_scaled[1, 1] *= scale_h
        K_scaled[0, 2] *= scale_w
        K_scaled[1, 2] *= scale_h

        E_w2c = np.linalg.inv(E_c2w)
        # P = K @ [R|t]  (3x4), padded to 4x4 with [0,0,0,1]
        P = K_scaled @ E_w2c[:3, :4]
        P_4x4 = np.eye(4, dtype=np.float32)
        P_4x4[:3, :4] = P
        return P_4x4

    def preprocess(self, images: List[np.ndarray], K_list: List[np.ndarray],
                   E_list: List[np.ndarray]) -> dict:
        """Build multi-scale images and projection matrices.

        Returns dict with keys:
            imgs: dict stage_0..stage_3 → tensor [1, N, 3, H_l, W_l]
            proj_matrices: dict stage_0..stage_3 → tensor [1, N, 4, 4]
        """
        N = len(images)
        H_orig, W_orig = images[0].shape[:2]

        # Multi-scale resolutions (feature net uses 1/8, 1/4, 1/2, 1/1)
        stages = {
            'stage_3': (H_orig // 8, W_orig // 8),
            'stage_2': (H_orig // 4, W_orig // 4),
            'stage_1': (H_orig // 2, W_orig // 2),
            'stage_0': (H_orig, W_orig),
        }

        imgs_dict = {}
        proj_dict = {}

        for stage_name, (H_s, W_s) in stages.items():
            scale_h = H_s / H_orig
            scale_w = W_s / W_orig

            # Resize images
            imgs_stage = []
            for img in images:
                import cv2
                img_resized = cv2.resize(img, (W_s, H_s), interpolation=cv2.INTER_AREA)
                # HWC → CHW, normalize to [0,1]
                img_t = torch.from_numpy(img_resized).permute(2, 0, 1).float() / 255.0
                imgs_stage.append(img_t)
            imgs_stage = torch.stack(imgs_stage, dim=0)  # [N, 3, H, W]
            imgs_dict[stage_name] = imgs_stage.unsqueeze(0)  # [1, N, 3, H, W]

            # Build projection matrices
            projs_stage = []
            for i in range(N):
                P = self._build_proj_matrix(K_list[i], E_list[i],
                                            H_orig, W_orig, scale_h, scale_w)
                projs_stage.append(torch.from_numpy(P))
            projs_stage = torch.stack(projs_stage, dim=0)  # [N, 4, 4]
            proj_dict[stage_name] = projs_stage.unsqueeze(0)  # [1, N, 4, 4]

        return {'imgs': imgs_dict, 'proj_matrices': proj_dict}

    @torch.no_grad()
    def run(self, images: List[np.ndarray], intrinsics: List[np.ndarray],
            extrinsics: List[np.ndarray], ref_idx: int = 0,
            depth_min: Optional[float] = None, depth_max: Optional[float] = None,
            original_size: Optional[tuple] = None) -> Tuple[np.ndarray, np.ndarray]:
        """Run PatchMatchNet depth estimation.

        Args:
            images: List of [H, W, 3] uint8 images.
            intrinsics: List of [3, 3] intrinsics.
            extrinsics: List of [4, 4] camera-to-world matrices.
            ref_idx: Index of reference image.
            depth_min, depth_max: Depth range.
            original_size: (H, W) to upsample output to.

        Returns:
            depth_map: [H, W] float32 depth.
            confidence: [H, W] float32 confidence.
        """
        # Select views: ref + nearest neighbors
        N = len(images)
        indices = [ref_idx]
        for d in range(1, N):
            if ref_idx - d >= 0:
                indices.append(ref_idx - d)
            if ref_idx + d < N:
                indices.append(ref_idx + d)
            if len(indices) >= min(N, 5):
                break

        imgs_sel = [images[i] for i in indices]
        K_sel = [intrinsics[i] for i in indices]
        E_sel = [extrinsics[i] for i in indices]

        data = self.preprocess(imgs_sel, K_sel, E_sel)

        imgs_dict = {k: v.to(self.device) for k, v in data['imgs'].items()}
        proj_dict = {k: v.to(self.device) for k, v in data['proj_matrices'].items()}

        dmin_t = torch.tensor([depth_min], device=self.device)
        dmax_t = torch.tensor([depth_max], device=self.device)

        output = self.model(imgs_dict, proj_dict, dmin_t, dmax_t)

        # output format: {'refined_depth': {'stage_0': [B,1,H,W]}, 'photometric_confidence': [B,H,W]}
        depth = output['refined_depth']['stage_0']  # [B, 1, H, W]
        depth_np = depth.squeeze(0).squeeze(0).cpu().numpy()

        if 'photometric_confidence' in output:
            conf_np = output['photometric_confidence'].squeeze(0).cpu().numpy()
        else:
            conf_np = np.ones_like(depth_np, dtype=np.float32) * 0.5

        # Upsample if needed
        if original_size is not None:
            h_orig, w_orig = original_size
            d_t = torch.from_numpy(depth_np).unsqueeze(0).unsqueeze(0)
            c_t = torch.from_numpy(conf_np).unsqueeze(0).unsqueeze(0)
            depth_np = F.interpolate(d_t, size=(h_orig, w_orig),
                                     mode='bilinear', align_corners=False).squeeze().numpy()
            conf_np = F.interpolate(c_t, size=(h_orig, w_orig),
                                    mode='bilinear', align_corners=False).squeeze().numpy()

        return depth_np.astype(np.float32), conf_np.astype(np.float32)
