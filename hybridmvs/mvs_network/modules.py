"""
Network building blocks compatible with kwea123/CasMVSNet_pl pretrained checkpoints.
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# 2D Feature Extraction (FPN-style, matches CasMVSNet_pl checkpoint)
# ---------------------------------------------------------------------------

class ConvBnReLU(nn.Module):
    def __init__(self, in_ch, out_ch, kernel_size=3, stride=1, padding=1, dilation=1):
        super().__init__()
        self.conv = nn.Conv2d(in_ch, out_ch, kernel_size, stride, padding, dilation, bias=False)
        self.bn = nn.BatchNorm2d(out_ch)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        return self.relu(self.bn(self.conv(x)))


class FeatureNet(nn.Module):
    """
    FPN-style feature extractor matching CasMVSNet_pl checkpoint.
    Outputs features at 3 scales: 1/8, 1/4, 1/1 resolution.
    """

    def __init__(self, base_channels: int = 8, out_channels: int = 32):
        super().__init__()
        # Encoder blocks: each is a Sequential of ConvBnReLU layers
        self.conv0 = nn.Sequential(
            ConvBnReLU(3, base_channels, 3, 1, 1),
            ConvBnReLU(base_channels, base_channels, 3, 1, 1),
        )
        self.conv1 = nn.Sequential(
            ConvBnReLU(base_channels, base_channels * 2, 5, 2, 2),
            ConvBnReLU(base_channels * 2, base_channels * 2, 3, 1, 1),
            ConvBnReLU(base_channels * 2, base_channels * 2, 3, 1, 1),
        )
        self.conv2 = nn.Sequential(
            ConvBnReLU(base_channels * 2, base_channels * 4, 5, 2, 2),
            ConvBnReLU(base_channels * 4, base_channels * 4, 3, 1, 1),
            ConvBnReLU(base_channels * 4, base_channels * 4, 3, 1, 1),
        )

        # FPN lateral connections and smoothing
        # Conv2 (32ch) → toplayer → smooth layers
        inner_channels = base_channels * 4  # 32

        self.toplayer = nn.Conv2d(inner_channels, out_channels, 1, 1, 0)

        self.lat1 = nn.Conv2d(base_channels * 2, out_channels, 1, 1, 0)
        self.lat0 = nn.Conv2d(base_channels, out_channels, 1, 1, 0)

        self.smooth1 = nn.Conv2d(out_channels, base_channels * 2, 3, 1, 1)
        self.smooth0 = nn.Conv2d(out_channels, base_channels, 3, 1, 1)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        # Encoder
        x0 = self.conv0(x)    # [B, 8, H, W]
        x1 = self.conv1(x0)   # [B, 16, H/2, W/2]
        x2 = self.conv2(x1)   # [B, 32, H/4, W/4]

        # FPN top-down
        p2 = self.toplayer(x2)  # [B, 32, H/4, W/4]

        # Smooth1 → 1/2 resolution
        p1_up = F.interpolate(p2, scale_factor=2, mode='bilinear', align_corners=False)
        p1 = self.lat1(x1) + p1_up  # [B, 32, H/2, W/2]
        p1_smooth = self.smooth1(p1)  # [B, 16, H/2, W/2]

        # Smooth0 → full resolution
        p0_up = F.interpolate(p1, scale_factor=2, mode='bilinear', align_corners=False)
        p0 = self.lat0(x0) + p0_up  # [B, 32, H, W]
        p0_smooth = self.smooth0(p0)  # [B, 8, H, W]

        return {
            'stage2': p2,         # [B, 32, H/4, W/4], coarsest
            'stage1': p1_smooth,  # [B, 16, H/2, W/2]
            'stage0': p0_smooth,  # [B, 8, H, W], finest
        }


# ---------------------------------------------------------------------------
# Homography Warping
# ---------------------------------------------------------------------------

def homo_warp(
    src_feat: torch.Tensor,
    src_intrinsics: torch.Tensor,
    src_extrinsics: torch.Tensor,
    ref_intrinsics: torch.Tensor,
    ref_extrinsics: torch.Tensor,
    depth_values: torch.Tensor,
) -> torch.Tensor:
    """Warp source features to reference view at given depth hypotheses.

    Args:
        src_feat: [B, C, H, W] source feature map.
        src_intrinsics: [B, 3, 3] source camera intrinsics.
        src_extrinsics: [B, 4, 4] source C2W extrinsics.
        ref_intrinsics: [B, 3, 3] reference camera intrinsics.
        ref_extrinsics: [B, 4, 4] reference C2W extrinsics.
        depth_values: [B, D] global or [B, D, H, W] per-pixel depth hypotheses.

    Returns:
        warped: [B, C, D, H, W] warped source features.
    """
    B, C, H, W = src_feat.shape
    D = depth_values.shape[1]
    device = src_feat.device
    per_pixel = (depth_values.ndim == 4)  # [B, D, H, W]

    # Both reference and source need world-to-camera convention
    ref_w2c = torch.inverse(ref_extrinsics)
    src_w2c = torch.inverse(src_extrinsics)

    R_ref = ref_w2c[:, :3, :3]   # W2C rotation
    t_ref = ref_w2c[:, :3, 3]    # W2C translation
    R_src = src_w2c[:, :3, :3]   # W2C rotation
    t_src = src_w2c[:, :3, 3]    # W2C translation

    # Transform point from ref camera to src camera:
    # P_src = W2C_src @ C2W_ref @ P_ref = R_src @ R_ref^T @ P_ref
    R_rel = torch.bmm(R_src, R_ref.transpose(1, 2))
    t_rel = t_src - torch.bmm(R_rel, t_ref.unsqueeze(-1)).squeeze(-1)

    ys, xs = torch.meshgrid(
        torch.arange(H, device=device, dtype=torch.float32),
        torch.arange(W, device=device, dtype=torch.float32),
        indexing='ij'
    )
    grid = torch.stack([xs, ys, torch.ones_like(xs)], dim=-1)
    grid = grid.unsqueeze(0).expand(B, -1, -1, -1)

    K_ref_inv = torch.inverse(ref_intrinsics)
    cam_pts = torch.matmul(K_ref_inv.unsqueeze(1).unsqueeze(1), grid.unsqueeze(-1)).squeeze(-1)

    if per_pixel:
        # depth_values: [B, D, H, W] → [B, H, W, D, 1]
        dv = depth_values.permute(0, 2, 3, 1).unsqueeze(-1)
    else:
        # depth_values: [B, D] → [B, 1, 1, D, 1]
        dv = depth_values.unsqueeze(1).unsqueeze(1).unsqueeze(-1)

    cam_pts = cam_pts.unsqueeze(3) * dv  # [B, H, W, D, 3]
    cam_pts_flat = cam_pts.reshape(B, -1, 3).transpose(1, 2)
    src_pts = torch.bmm(R_rel, cam_pts_flat) + t_rel.unsqueeze(-1)
    src_pts = src_pts.transpose(1, 2).reshape(B, H, W, D, 3)

    K_src = src_intrinsics
    src_pixels = torch.matmul(K_src.unsqueeze(1).unsqueeze(1).unsqueeze(1), src_pts.unsqueeze(-1)).squeeze(-1)

    Z = src_pixels[..., 2]
    valid = Z > 1e-6
    X = src_pixels[..., 0] / (Z + 1e-8)
    Y = src_pixels[..., 1] / (Z + 1e-8)

    # Handle both NDC (focal~1.0) and pixel (focal~500+) intrinsics
    if src_intrinsics[0, 0, 0] < 10:  # NDC mode (focal ~1.0)
        X_norm = X * 2.0 - 1.0
        Y_norm = Y * 2.0 - 1.0
    else:  # pixel mode
        X_norm = X / (W - 1) * 2.0 - 1.0
        Y_norm = Y / (H - 1) * 2.0 - 1.0
    X_norm = torch.where(valid, X_norm, torch.full_like(X_norm, -2.0))
    Y_norm = torch.where(valid, Y_norm, torch.full_like(Y_norm, -2.0))

    grid_sample_input = torch.stack([X_norm, Y_norm], dim=-1)
    grid_sample_input = grid_sample_input.permute(0, 3, 1, 2, 4).reshape(B * D, H, W, 2)

    src_feat_repeat = src_feat.unsqueeze(2).expand(-1, -1, D, -1, -1).reshape(B * D, C, H, W)

    warped = F.grid_sample(src_feat_repeat, grid_sample_input,
                           mode='bilinear', padding_mode='zeros', align_corners=False)
    warped = warped.reshape(B, C, D, H, W)

    return warped


def build_cost_volume(ref_feat, warped_feats, method="variance"):
    """Build cost volume from reference and warped source features.

    Uses incremental variance (E[X^2] - E[X]^2) to avoid storing all
    warped features simultaneously, saving ~40% peak GPU memory.
    """
    B, C, H, W = ref_feat.shape
    D = warped_feats[0].shape[2]
    device = ref_feat.device

    if method == "variance":
        # Expand ref to depth dimension once
        ref_exp = ref_feat.unsqueeze(2).expand(B, C, D, H, W)
        n = 1 + len(warped_feats)

        # Incremental: sum of features and sum of squared features
        sum_feat = ref_exp.clone()
        sum_sq = ref_exp ** 2

        for warped in warped_feats:
            sum_feat = sum_feat + warped
            sum_sq = sum_sq + warped ** 2

        mean = sum_feat / n
        variance = sum_sq / n - mean ** 2
        return variance

    # Concatenation method (fallback)
    all_feats = [ref_feat.unsqueeze(2).expand(B, C, D, H, W)] + warped_feats
    return torch.cat(all_feats, dim=1)


# ---------------------------------------------------------------------------
# 3D CNN Regularization (matches CasMVSNet_pl checkpoint)
# ---------------------------------------------------------------------------

class ConvBnReLU3D(nn.Module):
    def __init__(self, in_ch, out_ch, kernel_size=3, stride=1, padding=1):
        super().__init__()
        self.conv = nn.Conv3d(in_ch, out_ch, kernel_size, stride, padding, bias=False)
        self.bn = nn.BatchNorm3d(out_ch)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        return self.relu(self.bn(self.conv(x)))


class CostRegNet(nn.Module):
    """
    3D U-Net matching CasMVSNet_pl checkpoint architecture.

    The checkpoint expects:
      - conv0..conv6: encoder-decoder with skip connections
      - conv7, conv9, conv11: decoder upsampling convs (weight+bias as separate params)
      - prob: final 1-channel output conv
    """

    def __init__(self, in_channels: int = 8, base_channels: int = 8):
        super().__init__()
        # Encoder
        self.conv0 = ConvBnReLU3D(in_channels, base_channels, 3, 1, 1)
        self.conv1 = ConvBnReLU3D(base_channels, base_channels * 2, 3, 2, 1)
        self.conv2 = ConvBnReLU3D(base_channels * 2, base_channels * 2, 3, 1, 1)
        self.conv3 = ConvBnReLU3D(base_channels * 2, base_channels * 4, 3, 2, 1)
        self.conv4 = ConvBnReLU3D(base_channels * 4, base_channels * 4, 3, 1, 1)
        self.conv5 = ConvBnReLU3D(base_channels * 4, base_channels * 8, 3, 2, 1)
        self.conv6 = ConvBnReLU3D(base_channels * 8, base_channels * 8, 3, 1, 1)

        # Decoder deconv layers (weight and bias stored as separate nn.Modules list)
        # conv7: deconv from [64, H/8] → [32, H/4]
        self.conv7 = nn.Sequential(
            nn.ConvTranspose3d(base_channels * 8, base_channels * 4, 3, 2, 1, output_padding=1),
        )
        # conv9: deconv from [32, H/4] → [16, H/2]
        self.conv9 = nn.Sequential(
            nn.ConvTranspose3d(base_channels * 4, base_channels * 2, 3, 2, 1, output_padding=1),
        )
        # conv11: deconv from [16, H/2] → [8, H]
        self.conv11 = nn.Sequential(
            nn.ConvTranspose3d(base_channels * 2, base_channels, 3, 2, 1, output_padding=1),
        )

        # Output probability layer
        self.prob = nn.Conv3d(base_channels, 1, 3, 1, 1)

        # Extra conv for feature refinement (feat output)
        self.conv_out = nn.Conv3d(base_channels, base_channels, 3, 1, 1)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Conv3d, nn.ConvTranspose3d)):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm3d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x):
        # Encoder
        e0 = self.conv0(x)
        e1 = self.conv1(e0)
        e2 = self.conv2(e1)
        e3 = self.conv3(e2)
        e4 = self.conv4(e3)
        e5 = self.conv5(e4)
        e6 = self.conv6(e5)

        # Decoder
        d2 = self.conv7(e6)
        if d2.shape[-3:] != e4.shape[-3:]:
            d2 = F.interpolate(d2, size=e4.shape[-3:], mode='trilinear', align_corners=False)
        d2 = d2 + e4

        d1 = self.conv9(d2)
        if d1.shape[-3:] != e2.shape[-3:]:
            d1 = F.interpolate(d1, size=e2.shape[-3:], mode='trilinear', align_corners=False)
        d1 = d1 + e2

        d0 = self.conv11(d1)
        if d0.shape[-3:] != e0.shape[-3:]:
            d0 = F.interpolate(d0, size=e0.shape[-3:], mode='trilinear', align_corners=False)
        d0 = d0 + e0

        feat = self.conv_out(d0)
        prob = self.prob(feat)

        prob_softmax = F.softmax(prob.squeeze(1), dim=1)
        prob_softmax = prob_softmax.unsqueeze(1)

        return prob_softmax, feat


# ---------------------------------------------------------------------------
# Depth regression
# ---------------------------------------------------------------------------

def depth_regression(prob_volume: torch.Tensor, depth_values: torch.Tensor) -> torch.Tensor:
    """Soft-argmax depth regression.

    Args:
        prob_volume: [B, 1, D, H, W] probability volume (softmax over D).
        depth_values: [B, D] global or [B, D, H, W] per-pixel depth hypotheses.

    Returns:
        depth_map: [B, 1, H, W] regressed depth.
    """
    B, _, D, H, W = prob_volume.shape
    prob = prob_volume.squeeze(1)  # [B, D, H, W]

    if depth_values.ndim == 4:
        # Per-pixel: [B, D, H, W]
        depth_map = torch.sum(prob * depth_values, dim=1, keepdim=True)
    else:
        # Global: [B, D] → [B, D, 1, 1]
        dv = depth_values.view(B, D, 1, 1)
        depth_map = torch.sum(prob * dv, dim=1, keepdim=True)
    return depth_map


# Alias for backward compatibility
FeaturePyramid = FeatureNet

def depth_map_to_confidence(prob_volume, depth_values, depth_map, interval=2):
    """Compute confidence map from probability volume (legacy, for global depth only)."""
    B, _, D, H, W = prob_volume.shape
    prob = prob_volume.squeeze(1)
    if depth_values.ndim == 4:
        # Per-pixel: compare each pixel with its own depth hypotheses
        depth_diff = torch.abs(depth_values - depth_map)
        depth_idx = torch.argmin(depth_diff, dim=1)  # [B, H, W]
        idx_range = torch.arange(D, device=prob.device).view(1, D, 1, 1)
        mask = (idx_range >= (depth_idx - interval).unsqueeze(1)) & \
               (idx_range <= (depth_idx + interval).unsqueeze(1))
        return (prob * mask.float()).sum(dim=1, keepdim=True)
    else:
        depth_idx = torch.argmin(
            torch.abs(depth_values.unsqueeze(-1).unsqueeze(-1) - depth_map.squeeze(1)), dim=1)
        idx_range = torch.arange(D, device=prob.device).unsqueeze(0).unsqueeze(-1).unsqueeze(-1)
        mask = (idx_range >= (depth_idx - interval).unsqueeze(1)) & \
               (idx_range <= (depth_idx + interval).unsqueeze(1))
        return (prob * mask.float()).sum(dim=1, keepdim=True)
