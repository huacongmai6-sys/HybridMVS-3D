"""
End-to-end test with synthetic multi-view images.

Generates synthetic images of a 3D sphere, then runs:
  1. MVS depth estimation (CasMVSNet)
  2. Depth map fusion to dense point cloud
  3. Save as PLY

No COLMAP dependency for this test.
"""

import os
import sys
import numpy as np
import cv2

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from hybridmvs.mvs_network import MVSInference
from hybridmvs.mvs_network.inference import MVSConfig
from hybridmvs.fusion import DenseFusion


# ---------------------------------------------------------------------------
# Synthetic scene generator
# ---------------------------------------------------------------------------

def generate_synthetic_scene(
    num_views: int = 5,
    img_size: tuple = (640, 512),
    sphere_radius: float = 1.0,
    scene_depth: float = 5.0,
    noise_std: float = 2.0,
) -> dict:
    """
    Generate synthetic multi-view images of a textured sphere.

    Cameras are placed on an arc looking at the origin.

    Returns:
        Dict with 'images', 'intrinsics', 'extrinsics', 'gt_depths'.
    """
    w, h = img_size

    # Virtual camera intrinsics
    f = w * 0.8  # focal length in pixels
    K = np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1]], dtype=np.float64)

    images = []
    extrinsics = []
    intrinsics = []
    gt_depths = []

    # Generate camera positions in an arc around the Y axis
    for i in range(num_views):
        angle = np.deg2rad(-30 + 60 * i / (num_views - 1))  # -30 to +30 degrees

        # Camera center on a circle in XZ plane
        cx = np.sin(angle) * scene_depth
        cy = 0.0
        cz = np.cos(angle) * scene_depth

        # Camera-to-world matrix
        # Camera looks at origin from (cx, cy, cz)
        z_axis = -np.array([cx, cy, cz])
        z_axis = z_axis / np.linalg.norm(z_axis)
        y_axis = np.array([0, 1, 0])
        x_axis = np.cross(y_axis, z_axis)
        x_axis = x_axis / np.linalg.norm(x_axis)
        y_axis = np.cross(z_axis, x_axis)

        c2w = np.eye(4)
        c2w[:3, 0] = x_axis
        c2w[:3, 1] = y_axis
        c2w[:3, 2] = z_axis
        c2w[:3, 3] = [cx, cy, cz]

        # Render image + depth
        img, depth = _render_sphere(w, h, K, c2w, sphere_radius, noise_std)

        images.append(img)
        intrinsics.append(K.copy())
        extrinsics.append(c2w)
        gt_depths.append(depth)

    return {
        'images': images,
        'intrinsics': intrinsics,
        'extrinsics': extrinsics,
        'gt_depths': gt_depths,
    }


def _render_sphere(w, h, K, c2w, radius, noise_std):
    """Ray-trace a colored sphere with checkerboard texture."""
    img = np.zeros((h, w, 3), dtype=np.uint8)
    depth = np.zeros((h, w), dtype=np.float32)

    # Camera params
    fx, fy = K[0, 0], K[1, 1]
    cx, cy = K[0, 2], K[1, 2]
    cam_center = c2w[:3, 3]

    # Generate rays in world space
    ys, xs = np.mgrid[0:h, 0:w]
    x_cam = (xs - cx) / fx
    y_cam = (ys - cy) / fy
    z_cam = np.ones_like(x_cam)

    # Ray directions in camera space
    rays_cam = np.stack([x_cam, y_cam, z_cam], axis=-1)  # [H, W, 3]

    # Transform to world space
    R = c2w[:3, :3]
    rays_world = (R @ rays_cam[..., None]).squeeze(-1)  # [H, W, 3]

    # Normalize
    norms = np.linalg.norm(rays_world, axis=-1, keepdims=True)
    ray_dirs = rays_world / (norms + 1e-8)

    # Ray-sphere intersection at origin
    # |cam_center + t * ray_dir|^2 = radius^2
    oc = cam_center  # [3]
    b = 2 * np.sum(ray_dirs * oc, axis=-1)  # [H, W]
    c_val = np.sum(oc ** 2) - radius ** 2
    discriminant = b ** 2 - 4 * c_val

    hit = discriminant >= 0
    sqrt_d = np.sqrt(np.maximum(discriminant, 0))
    t1 = (-b - sqrt_d) / 2.0
    t2 = (-b + sqrt_d) / 2.0

    # Take the closer positive intersection
    t = np.where((t1 > 0) & hit, t1, np.where((t2 > 0) & hit, t2, 0))

    # Compute hit points and normals
    pts = cam_center + ray_dirs * t[..., None]
    normals = pts / (np.linalg.norm(pts, axis=-1, keepdims=True) + 1e-8)

    # Checkerboard texture based on spherical coordinates
    theta = np.arctan2(normals[..., 0], normals[..., 2])  # longitude
    phi = np.arcsin(np.clip(normals[..., 1], -1, 1))       # latitude

    # Create checkerboard pattern
    u = (theta / np.pi + 1) * 8
    v = (phi / np.pi + 0.5) * 4
    checker = ((u.astype(int) + v.astype(int)) % 2 == 0)

    # Lighting (simple diffuse)
    light_dir = np.array([0.5, 0.7, 0.5])
    light_dir = light_dir / np.linalg.norm(light_dir)
    diffuse = np.clip(np.sum(normals * light_dir, axis=-1), 0.1, 1.0)

    # Colors
    base_color = np.where(checker[..., None], [220, 80, 60], [240, 220, 200])
    color = (base_color * diffuse[..., None]).astype(np.uint8)
    color = np.where(hit[..., None], color, [40, 42, 54])
    img = color.astype(np.uint8)

    # Add noise
    if noise_std > 0:
        noise = np.random.normal(0, noise_std, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Depth map
    depth = np.where(hit, t, 0).astype(np.float32)

    return img, depth


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("HybridMVS - End-to-End Pipeline Test")
    print("=" * 60)

    output_dir = os.path.join(PROJECT_ROOT, "test_output")
    os.makedirs(output_dir, exist_ok=True)

    # ── 1. Generate synthetic scene ───────────────────────
    print("\n[1/3] Generating synthetic multi-view data...")
    scene = generate_synthetic_scene(num_views=5, img_size=(640, 512))
    print(f"  Generated {len(scene['images'])} views, "
          f"size: {scene['images'][0].shape}")

    # Save one view for inspection
    for i, img in enumerate(scene['images']):
        cv2.imwrite(
            os.path.join(output_dir, f"input_view_{i:02d}.png"),
            cv2.cvtColor(img, cv2.COLOR_RGB2BGR),
        )

    # ── 2. MVS Depth Estimation ─────────────────────────
    print("\n[2/3] Running MVS depth estimation...")

    mvs_cfg = MVSConfig(
        model_type="casmvsnet",
        num_views=5,
        min_depth=2.0,
        max_depth=10.0,
        img_height=512,
        img_width=640,
        device="cuda",
    )

    inference = MVSInference(mvs_cfg)

    all_depth_maps = []
    all_conf_maps = []

    for i in range(len(scene['images'])):
        depth, conf = inference.run(
            scene['images'],
            scene['intrinsics'],
            scene['extrinsics'],
            ref_idx=i,
            depth_min=2.0,
            depth_max=10.0,
        )
        all_depth_maps.append(depth)
        all_conf_maps.append(conf)
        print(f"  View {i + 1}/{len(scene['images'])}: "
              f"depth range [{depth.min():.2f}, {depth.max():.2f}], "
              f"mean confidence: {conf.mean():.3f}")

    # Save depth maps for inspection
    for i, (d, c) in enumerate(zip(all_depth_maps, all_conf_maps)):
        d_vis = np.clip(d / d.max() * 255, 0, 255).astype(np.uint8)
        cv2.imwrite(os.path.join(output_dir, f"depth_{i:02d}.png"), d_vis)
        c_vis = (c * 255).astype(np.uint8)
        cv2.imwrite(os.path.join(output_dir, f"confidence_{i:02d}.png"), c_vis)

    # ── 3. Dense Fusion ──────────────────────────────────
    print("\n[3/3] Fusing depth maps to dense point cloud...")

    fusion = DenseFusion(consistency_threshold=0.05, min_views=2, voxel_size=0.02)

    # Use the synthetic images for colors
    dense_points = fusion.fuse_depth_maps(
        all_depth_maps,
        scene['intrinsics'],
        scene['extrinsics'],
        images=scene['images'],
        confidence_maps=all_conf_maps,
        min_confidence=0.2,
    )
    print(f"  Fused: {len(dense_points)} points")

    # Consistency filter
    dense_points = fusion.filter_by_consistency(
        dense_points, all_depth_maps,
        scene['intrinsics'], scene['extrinsics'],
    )

    # Downsample
    dense_points = fusion.downsample(dense_points)
    print(f"  After filtering + downsampling: {len(dense_points)} points")

    # Save
    ply_path = fusion.save_point_cloud(dense_points, os.path.join(output_dir, "dense.ply"), fmt="ply")
    obj_path = fusion.save_point_cloud(dense_points, os.path.join(output_dir, "dense.obj"), fmt="obj")

    # ── Summary ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Test Complete!")
    print(f"  Output: {output_dir}")
    print(f"  Dense points: {len(dense_points)}")
    print(f"  Files: dense.ply, dense.obj, input_view_*.png, depth_*.png")
    print("=" * 60)


if __name__ == "__main__":
    main()
