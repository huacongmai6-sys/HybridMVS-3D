"""
Dense fusion module.

Fuses depth maps from the deep learning MVS network into a dense 3D point cloud.
Implements the standard DTU/CasMVSNet multi-view geometric consistency filter:
first filter each depth map against all other views, then fuse surviving pixels.
"""

import os
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False

logger = logging.getLogger(__name__)


class DenseFusion:
    """Standard DTU-style multi-view depth fusion with geometric consistency."""

    def __init__(
        self,
        consistency_threshold: float = 0.01,
        min_views: int = 3,
        voxel_size: Optional[float] = None,
    ):
        """
        Args:
            consistency_threshold: Max relative depth difference for consistency.
            min_views: Minimum total views (ref + src) that must agree to keep a point.
                       DTU standard is 3. Set to 2 for minimal filtering.
            voxel_size: Voxel size for point cloud downsampling (None = auto).
        """
        self.consistency_threshold = consistency_threshold
        self.min_views = min_views
        self.voxel_size = voxel_size

    # ── Core: per-view consistency filter ────────────────────────────

    def _check_consistency_one_view(
        self,
        pts_world: np.ndarray,
        src_depth: np.ndarray,
        src_K: np.ndarray,
        src_E: np.ndarray,
        threshold: float,
    ) -> np.ndarray:
        """Check geometric consistency of world points against one source view.

        Args:
            pts_world: [M, 3] world coordinates.
            src_depth: [H, W] source depth map.
            src_K: [3, 3] source intrinsics (must match depth map resolution).
            src_E: [4, 4] source camera-to-world extrinsics.
            threshold: Max relative depth difference.

        Returns:
            consistent: [M] bool array, True where point is consistent.
        """
        M = len(pts_world)
        if M == 0:
            return np.zeros(0, dtype=bool)

        # World → source camera
        E_inv = np.linalg.inv(src_E)
        R_inv = E_inv[:3, :3]
        t_inv = E_inv[:3, 3]
        pts_cam = (R_inv @ pts_world.T + t_inv.reshape(3, 1)).T  # [M, 3]

        Z = pts_cam[:, 2]
        in_front = Z > 1e-6
        if not in_front.any():
            return np.zeros(M, dtype=bool)

        # Project to image
        fx, fy = src_K[0, 0], src_K[1, 1]
        cx, cy = src_K[0, 2], src_K[1, 2]
        Hs, Ws = src_depth.shape

        u = np.full(M, -1, dtype=int)
        v = np.full(M, -1, dtype=int)
        u[in_front] = (pts_cam[in_front, 0] * fx / Z[in_front] + cx).astype(int)
        v[in_front] = (pts_cam[in_front, 1] * fy / Z[in_front] + cy).astype(int)

        in_bounds = (u >= 0) & (u < Ws) & (v >= 0) & (v < Hs) & in_front
        if not in_bounds.any():
            return np.zeros(M, dtype=bool)

        # Read observed depth at projected pixel
        obs_depth = np.full(M, -1.0)
        idx = in_bounds
        obs_depth[idx] = src_depth[v[idx], u[idx]]
        valid_obs = idx & (obs_depth > 0) & np.isfinite(obs_depth)
        if not valid_obs.any():
            return np.zeros(M, dtype=bool)

        # Relative depth difference
        rel_diff = np.full(M, np.inf)
        ok = valid_obs
        rel_diff[ok] = np.abs(Z[ok] - obs_depth[ok]) / (obs_depth[ok] + 1e-8)

        return rel_diff < threshold

    def filter_depth_map(
        self,
        ref_depth: np.ndarray,
        ref_K: np.ndarray,
        ref_E: np.ndarray,
        ref_colors_flat: np.ndarray,
        src_depths: List[np.ndarray],
        src_Ks: List[np.ndarray],
        src_Es: List[np.ndarray],
    ) -> np.ndarray:
        """Filter a reference depth map by multi-view geometric consistency.

        For each valid pixel in the reference depth map:
        1. Unproject to 3D world coordinate.
        2. Reproject to every source view and compare depths.
        3. Keep if consistent in >= (self.min_views - 1) source views
           (the reference view itself always counts as 1).

        Args:
            ref_depth: [H, W] reference depth map.
            ref_K: [3, 3] reference intrinsics (matching ref_depth resolution).
            ref_E: [4, 4] reference C2W extrinsics.
            ref_colors_flat: [H*W, 3] flattened reference image colors (0-1 float).
            src_depths: List of source depth maps [H, W].
            src_Ks: List of source intrinsics.
            src_Es: List of source extrinsics.

        Returns:
            points: [N, 6] filtered point cloud (xyz + rgb), or empty array.
        """
        H, W = ref_depth.shape

        # Valid pixel mask (confidence pre-filter already applied)
        valid_mask = (ref_depth > 0) & np.isfinite(ref_depth)
        if not valid_mask.any():
            return np.zeros((0, 6), dtype=np.float32)

        ys, xs = np.where(valid_mask)
        depths = ref_depth[valid_mask]
        M = len(depths)

        # ── Unproject all valid ref pixels to world ──
        fx, fy = ref_K[0, 0], ref_K[1, 1]
        cx, cy = ref_K[0, 2], ref_K[1, 2]

        X_cam = (xs - cx) * depths / fx
        Y_cam = (ys - cy) * depths / fy
        Z_cam = depths

        pts_cam = np.stack([X_cam, Y_cam, Z_cam, np.ones(M)], axis=1)
        pts_world = (ref_E @ pts_cam.T).T[:, :3]  # [M, 3]

        # ── Check against each source view ──
        n_src_needed = max(1, self.min_views - 1)  # exclude ref view
        consistent_count = np.zeros(M, dtype=int)

        for src_depth, src_K, src_E in zip(src_depths, src_Ks, src_Es):
            ok = self._check_consistency_one_view(
                pts_world, src_depth, src_K, src_E, self.consistency_threshold,
            )
            consistent_count += ok.astype(int)

            # Early exit if we already have enough views
            # (can't early-exit because we need to count ALL consistent views)

        # ── Keep pixels with enough consistent source views ──
        keep = consistent_count >= n_src_needed

        if not keep.any():
            return np.zeros((0, 6), dtype=np.float32)

        pts_keep = pts_world[keep]
        clr_keep = ref_colors_flat[valid_mask.flatten()][keep]

        result = np.hstack([pts_keep, clr_keep]).astype(np.float32)
        return result

    # ── Main fusion entry point ──────────────────────────────────────

    def fuse_depth_maps(
        self,
        depth_maps: List[np.ndarray],
        intrinsics: List[np.ndarray],
        extrinsics: List[np.ndarray],
        images: Optional[List[np.ndarray]] = None,
        confidence_maps: Optional[List[np.ndarray]] = None,
        min_confidence: float = 0.3,
    ) -> np.ndarray:
        """Fuse depth maps into a dense point cloud with consistency filtering.

        For each reference view:
        1. Pre-filter by confidence (if confidence maps provided).
        2. Filter each pixel by multi-view geometric consistency against
           all OTHER views (standard DTU/CasMVSNet protocol).
        3. Only surviving pixels are unprojected and collected.
        4. Merge all views' surviving points.

        Args:
            depth_maps: List of [H, W] float32 depth maps.
            intrinsics: List of [3, 3] intrinsics (matching depth map resolution).
            extrinsics: List of [4, 4] camera-to-world matrices.
            images: Optional list of [H, W, 3] images for colors.
            confidence_maps: Optional list of [H, W] confidence values.
            min_confidence: Pre-filter threshold (applied before consistency).

        Returns:
            points: [N, 6] array (x, y, z, r, g, b) as float32.
        """
        n_views = len(depth_maps)
        if images is None:
            images = [None] * n_views

        all_points = []

        for i in range(n_views):
            ref_depth = depth_maps[i].copy()
            H, W = ref_depth.shape

            # Pre-filter by confidence
            if confidence_maps is not None and i < len(confidence_maps):
                ref_depth[confidence_maps[i] < min_confidence] = 0.0

            # Prepare colors flattened to [H*W, 3]
            if images is not None and i < len(images) and images[i] is not None:
                img = images[i]
                if img.shape[:2] != (H, W):
                    import cv2
                    img = cv2.resize(img, (W, H))
                colors_flat = img.reshape(-1, 3).astype(np.float32) / 255.0
            else:
                colors_flat = np.zeros((H * W, 3), dtype=np.float32)

            # Source views: all views EXCEPT this one
            src_indices = [j for j in range(n_views) if j != i]
            src_depths = [depth_maps[j] for j in src_indices]
            src_Ks = [intrinsics[j] for j in src_indices]
            src_Es = [extrinsics[j] for j in src_indices]

            # Per-view consistency filter + unproject
            pts_i = self.filter_depth_map(
                ref_depth, intrinsics[i], extrinsics[i], colors_flat,
                src_depths, src_Ks, src_Es,
            )

            if len(pts_i) > 0:
                all_points.append(pts_i)

        if not all_points:
            logger.warning("No valid points after fusion")
            return np.zeros((0, 6), dtype=np.float32)

        result = np.vstack(all_points)
        logger.info(
            f"Fused {len(result)} points from {n_views} depth maps "
            f"(threshold={self.consistency_threshold}, min_views={self.min_views})"
        )
        return result

    # ── Downsample ───────────────────────────────────────────────────

    def downsample(self, points: np.ndarray, voxel_size: Optional[float] = None) -> np.ndarray:
        """Downsample point cloud using voxel grid filter."""
        if not HAS_OPEN3D:
            logger.warning("open3d not available; returning original points.")
            return points

        if len(points) == 0:
            return points

        if voxel_size is None:
            extent = np.ptp(points[:, :3], axis=0)
            voxel_size = np.mean(extent) * 0.005
            voxel_size = max(voxel_size, 1e-6)

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points[:, :3].astype(np.float64))
        if points.shape[1] >= 6:
            pcd.colors = o3d.utility.Vector3dVector(points[:, 3:6].astype(np.float64))

        pcd_down = pcd.voxel_down_sample(voxel_size)
        pts = np.asarray(pcd_down.points, dtype=np.float32)
        colors = np.asarray(pcd_down.colors, dtype=np.float32)

        result = np.hstack([pts, colors])
        logger.info(f"Downsampled: {len(points)} → {len(result)} points "
                     f"(voxel={voxel_size:.4f})")
        return result

    # ── I/O ──────────────────────────────────────────────────────────

    def save_point_cloud(
        self, points: np.ndarray, path: str, fmt: Optional[str] = None,
    ) -> str:
        """Save point cloud to file (ply/obj/xyz)."""
        if fmt is None:
            fmt = os.path.splitext(path)[1].lstrip('.').lower()

        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)

        if fmt == "ply":
            self._write_ply(path, points)
        elif fmt == "obj":
            self._write_obj(path, points)
        elif fmt == "xyz":
            np.savetxt(path, points[:, :3], fmt='%.6f')
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        logger.info(f"Saved point cloud to {path} ({len(points)} points)")
        return path

    def _write_ply(self, path: str, points: np.ndarray) -> None:
        n = len(points)
        has_color = points.shape[1] >= 6
        with open(path, 'w') as f:
            f.write("ply\nformat ascii 1.0\n")
            f.write(f"element vertex {n}\n")
            f.write("property float x\nproperty float y\nproperty float z\n")
            if has_color:
                f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
            f.write("end_header\n")
            for i in range(n):
                x, y, z = points[i, :3]
                if has_color:
                    r = int(min(255, max(0, points[i, 3] * 255)))
                    g = int(min(255, max(0, points[i, 4] * 255)))
                    b = int(min(255, max(0, points[i, 5] * 255)))
                    f.write(f"{x:.6f} {y:.6f} {z:.6f} {r} {g} {b}\n")
                else:
                    f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")

    def _write_obj(self, path: str, points: np.ndarray) -> None:
        with open(path, 'w') as f:
            f.write("# Point cloud exported by HybridMVS\n")
            for i in range(len(points)):
                x, y, z = points[i, :3]
                r, g, b = points[i, 3:6] if points.shape[1] >= 6 else (0.5, 0.5, 0.5)
                f.write(f"v {x:.6f} {y:.6f} {z:.6f} {r:.3f} {g:.3f} {b:.3f}\n")

    @staticmethod
    def load_point_cloud(path: str) -> np.ndarray:
        """Load a point cloud from file."""
        if HAS_OPEN3D:
            pcd = o3d.io.read_point_cloud(path)
            pts = np.asarray(pcd.points, dtype=np.float32)
            colors = np.asarray(pcd.colors, dtype=np.float32)
            if colors.shape[0] == pts.shape[0]:
                return np.hstack([pts, colors])
            return pts
        ext = os.path.splitext(path)[1].lower()
        if ext == '.ply':
            return DenseFusion._read_ply_raw(path)
        raise RuntimeError("open3d not available for reading point clouds")

    @staticmethod
    def _read_ply_raw(path: str) -> np.ndarray:
        with open(path, 'r') as f:
            lines = f.readlines()
        header_end = 0
        n_vertices = 0
        has_color = False
        for i, line in enumerate(lines):
            if line.startswith("element vertex"):
                n_vertices = int(line.split()[-1])
            if "uchar red" in line:
                has_color = True
            if line.strip() == "end_header":
                header_end = i + 1
                break
        data = []
        for line in lines[header_end:header_end + n_vertices]:
            parts = line.strip().split()
            if has_color:
                data.append([float(parts[0]), float(parts[1]), float(parts[2]),
                             float(parts[3])/255, float(parts[4])/255, float(parts[5])/255])
            else:
                data.append([float(parts[0]), float(parts[1]), float(parts[2])])
        return np.array(data, dtype=np.float32) if data else np.zeros((0, 3), dtype=np.float32)
