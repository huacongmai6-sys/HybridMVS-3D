"""
CasMVSNet: Cascade cost volume for high-resolution multi-view stereo.
Reference: Gu et al., "Cascade Cost Volume for High-Resolution Multi-View Stereo
           and Stereo Matching", CVPR 2020.

Architecture is compatible with kwea123/CasMVSNet_pl pretrained checkpoints.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional

from .modules import (
    FeatureNet, CostRegNet, homo_warp,
    build_cost_volume, depth_regression,
)


class CasMVSNet(nn.Module):
    """
    Cascade MVSNet with 3 refinement stages.

    Stage 2 (coarsest): 1/4 resolution, wide depth range
    Stage 1 (medium):   1/2 resolution, narrowed depth range
    Stage 0 (finest):   full resolution, narrowest range
    """

    def __init__(
        self,
        base_channels: int = 8,
        feat_channels: int = 32,
        depth_planes: List[int] = None,
        min_depth: float = 0.5,
        max_depth: float = 100.0,
    ):
        super().__init__()
        self.depth_planes = depth_planes or [128, 64, 48]
        self.min_depth = min_depth
        self.max_depth = max_depth

        # Shared feature extractor (named 'feature' to match pretrained checkpoint)
        self.feature = FeatureNet(
            base_channels=base_channels,
            out_channels=feat_channels,
        )

        # Stage-specific 3D regularization networks.
        # Named cost_reg_0/1/2 to match pretrained checkpoint (0=coarsest, 2=finest).
        # Each cost_reg processes a feature group of 8 channels.
        self.cost_reg_0 = CostRegNet(in_channels=8, base_channels=8)
        self.cost_reg_1 = CostRegNet(in_channels=8, base_channels=8)
        self.cost_reg_2 = CostRegNet(in_channels=8, base_channels=8)

    def _get_depth_values(self, B: int, device: torch.device,
                          depth_min: torch.Tensor, depth_max: torch.Tensor,
                          D: int, H: int = None, W: int = None) -> torch.Tensor:
        """Generate depth hypotheses, global [B, D] or per-pixel [B, D, H, W]."""
        d_min = depth_min.float()
        d_max = depth_max.float()

        if d_min.ndim >= 3:
            # Per-pixel depth range: d_min/d_max are [B, 1, H, W]
            t = torch.linspace(0, 1, D, device=device)
            t = t.view(1, D, 1, 1)
            i_d_min = 1.0 / d_min.clamp(min=1e-6)
            i_d_max = 1.0 / d_max.clamp(min=1e-6)
            i_d = i_d_min + (i_d_max - i_d_min) * t
            return 1.0 / i_d.clamp(min=1e-8)  # [B, D, H, W]

        i_d_min = 1.0 / d_min
        i_d_max = 1.0 / d_max
        t = torch.linspace(0, 1, D, device=device).unsqueeze(0)
        i_d = i_d_min.unsqueeze(-1) + (i_d_max - i_d_min).unsqueeze(-1) * t
        return 1.0 / i_d  # [B, D]

    def _compute_stage(
        self,
        feats: torch.Tensor,
        intrinsics: torch.Tensor,
        extrinsics: torch.Tensor,
        depth_min: torch.Tensor,
        depth_max: torch.Tensor,
        cost_reg_net: nn.Module,
        num_depth: int,
        in_channels: int,
        prev_depth: Optional[torch.Tensor] = None,
        prev_interval: Optional[float] = None,
    ) -> Dict[str, torch.Tensor]:
        B, N, C, H, W = feats.shape
        device = feats.device

        feats = feats[:, :, :in_channels]

        if prev_depth is not None and prev_interval is not None:
            # Upsample previous depth to current resolution
            prev_depth_up = F.interpolate(prev_depth, size=(H, W),
                                          mode='bilinear', align_corners=False)
            # Per-pixel depth range: ± half of num_depth * interval
            half_range = (num_depth / 2.0) * prev_interval
            depth_min = torch.clamp(prev_depth_up - half_range, min=1e-6)
            depth_max = prev_depth_up + half_range
            depth_values = self._get_depth_values(B, device, depth_min, depth_max,
                                                  num_depth, H, W)
        else:
            depth_values = self._get_depth_values(B, device, depth_min, depth_max,
                                                  num_depth)

        ref_feat = feats[:, 0]
        warped_feats = []
        for s in range(1, N):
            warped = homo_warp(
                feats[:, s], intrinsics[:, s], extrinsics[:, s],
                intrinsics[:, 0], extrinsics[:, 0], depth_values,
            )
            warped_feats.append(warped)

        cost_volume = build_cost_volume(ref_feat, warped_feats, method="variance")
        prob_volume, _ = cost_reg_net(cost_volume)
        depth_map = depth_regression(prob_volume, depth_values)

        return {
            'depth': depth_map,
            'prob_volume': prob_volume,
            'depth_values': depth_values,
        }

    def forward(
        self,
        imgs: torch.Tensor,
        intrinsics: torch.Tensor,
        extrinsics: torch.Tensor,
        depth_min: Optional[torch.Tensor] = None,
        depth_max: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        """Stage2-only MVS with global depth range and bilinear upsampling.

        Stage1/Stage0 are skipped because the FPN fine-scale features have
        uncontrolled magnitude on out-of-domain data (std 236-306 vs DTU
        expected ~1.0), causing cost_reg_1/2 probability collapse to one-hot.

        Stage2 (1/4 res, cost_reg_0, 128 global planes) produces healthy
        probability distributions (entropy ≈ 0.55) and geometrically
        consistent depth maps. Upsampled to full resolution via bilinear
        interpolation.
        """
        B, N, _, H, W = imgs.shape
        device = imgs.device

        if depth_min is None:
            depth_min = torch.full((B,), self.min_depth, device=device)
        if depth_max is None:
            depth_max = torch.full((B,), self.max_depth, device=device)

        # Shared feature extraction
        imgs_flat = imgs.reshape(B * N, 3, H, W)
        feats_dict = self.feature(imgs_flat)

        # ── Stage 2 only: coarsest (1/4 resolution, 128 global depth planes) ──
        s2_h, s2_w = feats_dict['stage2'].shape[-2:]
        feats_s2 = feats_dict['stage2'].reshape(B, N, -1, s2_h, s2_w)

        scale2_h = s2_h / H
        scale2_w = s2_w / W
        K_s2 = intrinsics.clone()
        K_s2[:, :, 0, 0] *= scale2_w
        K_s2[:, :, 1, 1] *= scale2_h
        K_s2[:, :, 0, 2] *= scale2_w
        K_s2[:, :, 1, 2] *= scale2_h

        result_s2 = self._compute_stage(
            feats_s2, K_s2, extrinsics,
            depth_min, depth_max, self.cost_reg_0,
            self.depth_planes[0], in_channels=8,
        )

        # Upsample stage2 depth to full resolution
        depth_s2 = result_s2['depth']  # [B, 1, H/4, W/4]
        depth_full = F.interpolate(depth_s2, size=(H, W),
                                   mode='bilinear', align_corners=False)

        return {
            'depth': depth_full,
            'prob_volume': result_s2['prob_volume'],
            'depth_values': result_s2['depth_values'],
            'prob_volume_stage2': result_s2['prob_volume'],
            'depth_values_stage2': result_s2['depth_values'],
        }
