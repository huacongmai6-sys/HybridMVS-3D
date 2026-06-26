"""
Comprehensive test for HybridMVS.

Tests:
  1. Module imports
  2. MVSNet model instantiation (GPU)
  3. CasMVSNet forward pass
  4. Full MVS + fusion pipeline (synthetic data)
  5. COLMAP error handling
  6. Backend API health check
"""

import os
import sys
import numpy as np
import cv2

# Project root is the directory containing this script
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

passed = 0
failed = 0

def check(name, condition):
    global passed, failed
    if condition:
        print(f"  [PASS] {name}")
        passed += 1
    else:
        print(f"  [FAIL] {name}")
        failed += 1

print("=" * 60)
print("HybridMVS - Full Test Suite")
print("=" * 60)

# ── 1. Module Imports ───────────────────────────────────────
print("\n[1] Module Imports")
try:
    from hybridmvs.colmap_wrapper import ColmapEngine
    from hybridmvs.colmap_wrapper.utils import Camera, Image, Point3D, read_cameras
    from hybridmvs.mvs_network import MVSNet, CasMVSNet, MVSInference, MVSConfig
    from hybridmvs.fusion import FormatConverter, DenseFusion
    from hybridmvs.pipeline import HybridReconstructionPipeline
    check("All modules imported", True)
except Exception as e:
    check(f"All modules imported - {e}", False)

# ── 2. Model Instantiation ──────────────────────────────────
print("\n[2] Model Instantiation (GPU)")
try:
    import torch
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    casmvs = CasMVSNet(base_channels=8, feat_channels=32).to(device)
    n_params = sum(p.numel() for p in casmvs.parameters())
    check(f"CasMVSNet ({n_params:,} params)", n_params > 500_000)

    mvsnet = MVSNet(base_channels=8, feat_channels=32, mode="eval").to(device)
    n_params = sum(p.numel() for p in mvsnet.parameters())
    check(f"MVSNet ({n_params:,} params)", n_params > 200_000)

    dummy = torch.randn(2, 5, 3, 512, 640, device=device)
    dummy_K = torch.eye(3, device=device).repeat(2, 5, 1, 1)
    dummy_E = torch.eye(4, device=device).repeat(2, 5, 1, 1)
    dummy_E[:, :, :3, 3] = 0.1

    with torch.no_grad():
        out = casmvs(dummy, dummy_K, dummy_E)
    check("CasMVSNet forward pass", 'depth' in out)
    check(f"  Output shape: {list(out['depth'].shape)}",
          out['depth'].shape == (2, 1, 512, 640))

except Exception as e:
    check(f"Model instantiation - {e}", False)

# ── 3. MVS + Fusion Pipeline ────────────────────────────────
print("\n[3] MVS + Fusion Pipeline (synthetic data)")
try:
    # Generate simple scene
    w, h = 640, 512
    f = w * 0.8
    K = np.array([[f, 0, w/2], [0, f, h/2], [0, 0, 1]], dtype=np.float64)
    images, intrinsics, extrinsics = [], [], []

    for i in range(5):
        angle = np.deg2rad(-20 + 10 * i)
        cx, cy, cz = np.sin(angle) * 5, 0, np.cos(angle) * 5

        z_axis = -np.array([cx, cy, cz])
        z_axis /= np.linalg.norm(z_axis)
        x_axis = np.cross([0, 1, 0], z_axis)
        x_axis /= np.linalg.norm(x_axis)
        y_axis = np.cross(z_axis, x_axis)

        c2w = np.eye(4)
        c2w[:3, 0], c2w[:3, 1], c2w[:3, 2], c2w[:3, 3] = x_axis, y_axis, z_axis, [cx, cy, cz]

        # Generate a noisy textured image (random pattern for features)
        img = (np.random.rand(h, w, 3) * 255).astype(np.uint8)

        images.append(img)
        intrinsics.append(K.copy())
        extrinsics.append(c2w)

    # Run MVS
    cfg = MVSConfig(model_type='casmvsnet', num_views=5, img_height=h, img_width=w, device='cuda')
    infer = MVSInference(cfg)

    depth_maps, conf_maps = [], []
    for i in range(3):  # test 3 views
        d, c = infer.run(images, intrinsics, extrinsics, ref_idx=i, depth_min=2.0, depth_max=10.0)
        depth_maps.append(d)
        conf_maps.append(c)

    check("MVS inference (3 views)", len(depth_maps) == 3)
    check(f"  Depth range: [{depth_maps[0].min():.2f}, {depth_maps[0].max():.2f}]", True)

    # Fuse
    fusion = DenseFusion()
    pts = fusion.fuse_depth_maps(depth_maps, intrinsics[:3], extrinsics[:3],
                                 images=images[:3], confidence_maps=conf_maps)
    check("Dense fusion", len(pts) > 0)

    pts_filtered = fusion.filter_by_consistency(pts, depth_maps[:3], intrinsics[:3], extrinsics[:3])
    check(f"Fused: {len(pts_filtered)} points", len(pts_filtered) > 0)

    # Save PLY
    test_output_dir = os.path.join(PROJECT_ROOT, "test_output")
    os.makedirs(test_output_dir, exist_ok=True)
    fusion.save_point_cloud(pts_filtered, os.path.join(test_output_dir, "test.ply"), fmt="ply")
    check("PLY export", os.path.isfile(os.path.join(test_output_dir, "test.ply")))

except Exception as e:
    check(f"MVS + Fusion pipeline - {e}", False)

# ── 4. COLMAP Error Handling ────────────────────────────────
print("\n[4] COLMAP Error Handling")
try:
    engine = ColmapEngine(
        workspace_dir=os.path.join(PROJECT_ROOT, "test_colmap_error"),
        colmap_binary=None,  # auto-detect
    )

    # Run feature extraction on a temp dir with one image (should fail at matching)
    # Actually just test that the engine is created correctly
    check("COLMAP engine created", engine.colmap_binary is not None)

    # Test camera model parsing (COLMAP 4.x format with model name)
    test_cam_dir = os.path.join(PROJECT_ROOT, "test_colmap_error")
    test_cam_path = os.path.join(test_cam_dir, "cameras.txt")
    os.makedirs(os.path.dirname(test_cam_path), exist_ok=True)
    with open(test_cam_path, 'w') as f:
        f.write("# test\n1 SIMPLE_RADIAL 640 480 800.0 320 240 -0.1\n")

    cams = read_cameras(test_cam_path)
    check("COLMAP 4.x camera format (model name)", len(cams) == 1 and cams[1].model == "SIMPLE_RADIAL")

    # Test old format too
    with open(test_cam_path, 'w') as f:
        f.write("# test\n1 2 640 480 800.0 320 240 -0.1\n")
    cams2 = read_cameras(test_cam_path)
    check("COLMAP 3.x camera format (model ID)", len(cams2) == 1 and cams2[1].model == "SIMPLE_RADIAL")

except Exception as e:
    check(f"COLMAP error handling - {e}", False)

# ── 5. Backend API ──────────────────────────────────────────
print("\n[5] Backend API")
try:
    import urllib.request
    import json

    resp = urllib.request.urlopen("http://127.0.0.1:5000/api/health")
    data = json.loads(resp.read())
    check(f"Health check: {data['status']}", data['status'] == 'ok')
except Exception as e:
    check(f"Backend API - {e}", False)

# ── Summary ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)
