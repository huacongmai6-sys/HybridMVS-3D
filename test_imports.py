"""Verify all HybridMVS modules import and instantiate correctly."""
import sys
sys.path.insert(0, 'd:/HybridMVS')

print("Testing module imports...")

# Test colmap utils
from hybridmvs.colmap_wrapper.utils import (
    Camera, Image, Point3D, qvec2rotmat, rotmat2qvec,
    read_cameras, read_images, read_points3d,
    write_cameras, write_images, write_points3d,
    load_colmap_model, save_colmap_model,
)
print("  colmap_wrapper.utils: OK")

# Test colmap engine
from hybridmvs.colmap_wrapper.colmap_engine import ColmapEngine
print("  colmap_wrapper.colmap_engine: OK")

# Test MVS modules
from hybridmvs.mvs_network.modules import (
    FeaturePyramid, CostRegNet, ConvBnReLU, ConvBnReLU3D,
    homo_warp, build_cost_volume, depth_regression, depth_map_to_confidence,
)
print("  mvs_network.modules: OK")

from hybridmvs.mvs_network.mvsnet import MVSNet, mvsnet_loss
print("  mvs_network.mvsnet: OK")

from hybridmvs.mvs_network.cas_mvsnet import CasMVSNet, casmvsnet_loss
print("  mvs_network.cas_mvsnet: OK")

from hybridmvs.mvs_network.inference import MVSInference, MVSConfig
print("  mvs_network.inference: OK")

# Test fusion modules
from hybridmvs.fusion.format_converter import FormatConverter
print("  fusion.format_converter: OK")

from hybridmvs.fusion.dense_fusion import DenseFusion
print("  fusion.dense_fusion: OK")

# Test main pipeline
from hybridmvs.pipeline import HybridReconstructionPipeline
print("  pipeline: OK")

# --- Test model instantiation ---
import torch
print("\nTesting model instantiation...")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"  Using device: {device}")

# Test MVSNet
mvsnet = MVSNet(base_channels=8, feat_channels=32, depth_planes=192, mode="eval")
mvsnet = mvsnet.to(device)
print(f"  MVSNet parameters: {sum(p.numel() for p in mvsnet.parameters()):,}")

# Test CasMVSNet
casmvs = CasMVSNet(base_channels=8, feat_channels=32)
casmvs = casmvs.to(device)
print(f"  CasMVSNet parameters: {sum(p.numel() for p in casmvs.parameters()):,}")

# Test FeaturePyramid
fp = FeaturePyramid(base_channels=8, out_channels=32).to(device)
dummy_img = torch.randn(2, 3, 512, 640, device=device)
with torch.no_grad():
    feats = fp(dummy_img)
print(f"  FeaturePyramid output stages: {list(feats.keys())}")
for k, v in feats.items():
    print(f"    {k}: {list(v.shape)}")

# Test CostRegNet
crn = CostRegNet(in_channels=32, base_channels=8).to(device)
dummy_cv = torch.randn(2, 32, 192, 128, 160, device=device)
with torch.no_grad():
    prob, feat = crn(dummy_cv)
print(f"  CostRegNet prob output: {list(prob.shape)}")

# Test homography warping
dummy_src_feat = torch.randn(2, 32, 128, 160, device=device)
dummy_src_K = torch.eye(3, device=device).unsqueeze(0).expand(2, -1, -1).clone()
dummy_src_K[:, 0, 0] = dummy_src_K[:, 1, 1] = 500.0
dummy_src_K[:, 0, 2] = 80.0
dummy_src_K[:, 1, 2] = 64.0
dummy_src_E = torch.eye(4, device=device).unsqueeze(0).expand(2, -1, -1).clone()
dummy_src_E[:, 0, 3] = 0.1
dummy_ref_K = dummy_src_K.clone()
dummy_ref_E = torch.eye(4, device=device).unsqueeze(0).expand(2, -1, -1).clone()
dummy_depths = torch.linspace(0.5, 10.0, 192, device=device).unsqueeze(0).expand(2, -1)

with torch.no_grad():
    warped = homo_warp(dummy_src_feat, dummy_src_K, dummy_src_E,
                       dummy_ref_K, dummy_ref_E, dummy_depths)
print(f"  homo_warp output: {list(warped.shape)}")

print("\nAll tests passed!")
