"""
MVSNet: End-to-end learning for multi-view stereo.
Reference: Yao et al., "MVSNet: Depth Inference for Unstructured Multi-view Stereo", ECCV 2018.

This implementation provides:
- Standard MVSNet with configurable depth planes
- Feature extraction with shared 2D CNN
- Homography-based cost volume construction
- 3D CNN regularization with soft-argmax depth regression
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional

from .modules import (
    FeatureNet, CostRegNet, homo_warp,
    build_cost_volume, depth_regression,
)


class MVSNet(nn.Module):
    """
    MVSNet architecture for depth estimation from multi-view images.

    Args:
        base_channels: Base channel count for feature extraction.
        feat_channels: Output feature channels.
        depth_planes: Number of depth hypotheses (default: 192).
        min_depth: Minimum depth in scene units.
        max_depth: Maximum depth in scene units.
        mode: "train" or "eval". In eval mode, outputs depth maps directly.
    """

    def __init__(
        self,
        base_channels: int = 8,
        feat_channels: int = 32,
        depth_planes: int = 192,
        min_depth: float = 0.5,
        max_depth: float = 100.0,
        mode: str = "train",
    ):
        super().__init__()
        self.depth_planes = depth_planes
        self.min_depth = min_depth
        self.max_depth = max_depth
        self.mode = mode

        self.feature_extractor = FeatureNet(
            base_channels=base_channels,
            out_channels=feat_channels,
        )
        self.cost_reg_net = CostRegNet(
            in_channels=8,
            base_channels=base_channels,
        )

    def _get_depth_values(self, batch_size: int, device: torch.device,
                          depth_min: Optional[torch.Tensor] = None,
                          depth_max: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Generate depth hypothesis planes, [B, D]."""
        if depth_min is None:
            depth_min = torch.full((batch_size,), self.min_depth, device=device)
        if depth_max is None:
            depth_max = torch.full((batch_size,), self.max_depth, device=device)

        depth_min = depth_min.float()
        depth_max = depth_max.float()

        # Linear spacing in inverse depth for better near-field sampling
        D = self.depth_planes
        i_d_min = 1.0 / depth_min
        i_d_max = 1.0 / depth_max
        i_d_vals = torch.linspace(0, 1, D, device=device).unsqueeze(0)
        i_d_samples = i_d_min.unsqueeze(-1) + (i_d_max - i_d_min).unsqueeze(-1) * i_d_vals
        depth_values = 1.0 / i_d_samples  # [B, D]

        return depth_values

    def forward(
        self,
        imgs: torch.Tensor,
        intrinsics: torch.Tensor,
        extrinsics: torch.Tensor,
        depth_min: Optional[torch.Tensor] = None,
        depth_max: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Args:
            imgs: [B, N, 3, H, W] multi-view images. imgs[:, 0] is reference.
            intrinsics: [B, N, 3, 3] camera intrinsics.
            extrinsics: [B, N, 4, 4] camera-to-world matrices.
            depth_min: [B] min depth per batch item (optional).
            depth_max: [B] max depth per batch item (optional).

        Returns:
            Dict with:
              - 'depth': [B, 1, H, W] regressed depth map.
              - 'prob_volume': [B, 1, D, H, W] probability volume.
              - 'depth_values': [B, D] depth hypothesis values.
        """
        B, N, _, H, W = imgs.shape
        device = imgs.device

        # Reshape for feature extraction
        imgs_flat = imgs.reshape(B * N, 3, H, W)
        feats_dict = self.feature_extractor(imgs_flat)
        feats = feats_dict['stage0']  # [B*N, C, H, W]
        feats = feats.reshape(B, N, -1, H, W)

        # Reference and source features
        ref_feat = feats[:, 0]  # [B, C, H, W]
        src_feats = feats[:, 1:]  # [B, N-1, C, H, W]

        # Generate depth hypotheses
        depth_values = self._get_depth_values(B, device, depth_min, depth_max)  # [B, D]

        # Warp source features to reference view at each depth
        warped_feats = []
        for s in range(N - 1):
            warped = homo_warp(
                src_feats[:, s],
                intrinsics[:, 1 + s],
                extrinsics[:, 1 + s],
                intrinsics[:, 0],
                extrinsics[:, 0],
                depth_values,
            )
            warped_feats.append(warped)

        # Build cost volume via variance aggregation
        cost_volume = build_cost_volume(ref_feat, warped_feats, method="variance")
        # [B, C, D, H, W]

        # 3D CNN regularization
        prob_volume, _ = self.cost_reg_net(cost_volume)
        # prob_volume: [B, 1, D, H, W]

        # Depth regression via soft-argmax
        depth_map = depth_regression(prob_volume, depth_values)  # [B, 1, H, W]

        return {
            'depth': depth_map,
            'prob_volume': prob_volume,
            'depth_values': depth_values,
        }


def mvsnet_loss(
    pred: Dict[str, torch.Tensor],
    gt_depth: torch.Tensor,
    gt_mask: Optional[torch.Tensor] = None,
) -> torch.Tensor:
    """
    Compute MVSNet L1 loss between predicted and ground truth depth.

    Args:
        pred: Model output dict with keys 'depth', 'depth_values'.
        gt_depth: [B, 1, H, W] ground truth depth.
        gt_mask: [B, 1, H, W] boolean mask for valid depth pixels.

    Returns:
        Scalar loss value.
    """
    pred_depth = pred['depth']
    if gt_mask is None:
        gt_mask = (gt_depth > 0) & torch.isfinite(gt_depth)

    diff = torch.abs(pred_depth - gt_depth)
    loss = (diff * gt_mask.float()).sum() / (gt_mask.float().sum() + 1e-8)
    return loss
