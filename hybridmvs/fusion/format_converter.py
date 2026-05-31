"""
Format converter: bridge between COLMAP data and deep learning MVS input/output.

Handles:
- COLMAP camera/intrinsics ↔ MVS network tensor format
- Depth maps ↔ COLMAP depth map format (for fusion)
- Coordinate system alignment
"""

import os
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

import cv2

logger = logging.getLogger(__name__)


class FormatConverter:
    """
    Converts between COLMAP's data structures and the deep learning
    MVS network's expected input/output formats.
    """

    @staticmethod
    def colmap_to_mvs_input(
        cameras: Dict[int, object],
        images: Dict[int, object],
        image_dir: str,
        target_height: int = 512,
        target_width: int = 640,
        max_images: Optional[int] = None,
    ) -> Tuple[List[np.ndarray], List[np.ndarray], List[np.ndarray], List[str]]:
        """
        Convert COLMAP model data to MVS network input format.

        Args:
            cameras: Dict of camera_id -> Camera from COLMAP utils.
            images: Dict of image_id -> Image from COLMAP utils.
            image_dir: Directory containing the image files.
            target_height, target_width: Target dimensions for network input.
            max_images: Limit number of images processed.

        Returns:
            img_list: List of [H, W, 3] uint8 images.
            K_list: List of [3, 3] intrinsic matrices.
            E_list: List of [4, 4] camera-to-world extrinsic matrices.
            name_list: List of image filenames.
        """
        img_list = []
        K_list = []
        E_list = []
        name_list = []

        sorted_images = sorted(images.items(), key=lambda x: x[0])
        if max_images:
            sorted_images = sorted_images[:max_images]

        for img_id, img_data in sorted_images:
            # Load image
            img_path = os.path.join(image_dir, img_data.name)
            if not os.path.isfile(img_path):
                logger.warning(f"Image not found: {img_path}")
                continue

            img = cv2.imread(img_path)
            if img is None:
                logger.warning(f"Failed to read image: {img_path}")
                continue
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Intrinsics
            cam = cameras[img_data.camera_id]
            K = cam.K.copy().astype(np.float64)  # 3x3 intrinsic matrix

            # Extrinsics (camera-to-world)
            E = img_data.camera_to_world.astype(np.float64)  # 4x4 matrix

            # Resize image and scale K to target resolution
            orig_h, orig_w = img.shape[:2]
            scale_h = target_height / orig_h
            scale_w = target_width / orig_w

            if abs(scale_h - 1.0) > 1e-6 or abs(scale_w - 1.0) > 1e-6:
                img = cv2.resize(img, (target_width, target_height),
                                 interpolation=cv2.INTER_AREA)
                K[0, 0] *= scale_w  # fx
                K[1, 1] *= scale_h  # fy
                K[0, 2] *= scale_w  # cx
                K[1, 2] *= scale_h  # cy

            img_list.append(img)
            K_list.append(K)
            E_list.append(E)
            name_list.append(img_data.name)

        logger.info(f"Loaded {len(img_list)} images for MVS input")
        return img_list, K_list, E_list, name_list

    @staticmethod
    def mvs_depth_to_colmap_format(
        depth_maps: List[np.ndarray],
        confidence_maps: Optional[List[np.ndarray]] = None,
        min_confidence: float = 0.3,
    ) -> List[np.ndarray]:
        """
        Convert MVS network depth maps to COLMAP-compatible format.

        COLMAP expects depth maps as 16-bit PNG where:
          depth_mm = pixel_value / 65535 * max_depth_mm
        Or as float32 .bin files.

        Here we produce float32 depth maps and apply confidence filtering.

        Args:
            depth_maps: List of [H, W] float32 depth values.
            confidence_maps: Optional list of [H, W] float32 confidence [0,1].
            min_confidence: Minimum confidence threshold.

        Returns:
            filtered_depth_maps: List of [H, W] float32 depth maps (invalid=0).
        """
        filtered = []
        for i, depth in enumerate(depth_maps):
            d = depth.copy()
            # Zero out invalid regions
            d[~np.isfinite(d)] = 0.0
            d[d <= 0] = 0.0

            if confidence_maps is not None and i < len(confidence_maps):
                d[confidence_maps[i] < min_confidence] = 0.0

            filtered.append(d)

        return filtered

    @staticmethod
    def save_depth_maps(
        depth_maps: List[np.ndarray],
        output_dir: str,
        image_names: Optional[List[str]] = None,
        fmt: str = "pfm",
    ) -> List[str]:
        """
        Save depth maps to disk in the specified format.

        Args:
            depth_maps: List of [H, W] float32 depth values.
            output_dir: Output directory.
            image_names: Image filenames (to derive depth filenames).
            fmt: Output format: "pfm", "npy", "png16", "bin".

        Returns:
            List of saved file paths.
        """
        os.makedirs(output_dir, exist_ok=True)
        paths = []

        for i, depth in enumerate(depth_maps):
            if image_names and i < len(image_names):
                base = os.path.splitext(image_names[i])[0]
            else:
                base = f"depth_{i:04d}"

            if fmt == "pfm":
                path = os.path.join(output_dir, f"{base}.pfm")
                FormatConverter._write_pfm(path, depth)
            elif fmt == "npy":
                path = os.path.join(output_dir, f"{base}.npy")
                np.save(path, depth)
            elif fmt == "png16":
                path = os.path.join(output_dir, f"{base}.png")
                depth_clipped = np.clip(depth, 0, 65535)
                depth_16 = (depth_clipped / depth_clipped.max() * 65535).astype(np.uint16) \
                    if depth_clipped.max() > 0 else np.zeros_like(depth, dtype=np.uint16)
                cv2.imwrite(path, depth_16)
            elif fmt == "bin":
                path = os.path.join(output_dir, f"{base}.bin")
                depth.astype(np.float32).tofile(path)
            else:
                raise ValueError(f"Unknown format: {fmt}")

            paths.append(path)

        logger.info(f"Saved {len(paths)} depth maps to {output_dir} (format: {fmt})")
        return paths

    @staticmethod
    def _write_pfm(path: str, image: np.ndarray) -> None:
        """Write a float32 array as a PFM file."""
        h, w = image.shape
        scale = -1.0  # little-endian

        header = f"Pf\n{w} {h}\n{scale}\n"
        with open(path, 'wb') as f:
            f.write(header.encode())
            f.write(np.flipud(image).astype(np.float32).tobytes())

    @staticmethod
    def _read_pfm(path: str) -> np.ndarray:
        """Read a PFM file into a float32 numpy array."""
        with open(path, 'rb') as f:
            header = f.readline().decode().strip()
            if header not in ('Pf', 'PF'):
                raise ValueError(f"Not a PFM file: {header}")

            dims = f.readline().decode().strip()
            w, h = map(int, dims.split())
            scale = float(f.readline().decode().strip())

            data = np.fromfile(f, dtype=np.float32).reshape(h, w)
            if scale > 0:
                data = np.flipud(data)  # big-endian
            return data

    @staticmethod
    def compute_depth_range(
        sparse_points: np.ndarray,
        camera_centers: np.ndarray,
        percentile: Tuple[float, float] = (1.0, 99.0),
        margin: float = 0.25,
    ) -> Tuple[float, float]:
        """
        Estimate scene depth range from sparse point cloud.

        Args:
            sparse_points: [N, 3] sparse 3D points from COLMAP.
            camera_centers: [M, 3] camera center positions.
            percentile: Percentile range for depth estimation.
            margin: Additional margin factor (0.25 = ±25%).

        Returns:
            min_depth, max_depth as floats.
        """
        if len(sparse_points) == 0 or len(camera_centers) == 0:
            return 0.5, 100.0

        # Compute distances from each camera to all points
        depths = []
        for center in camera_centers:
            dists = np.linalg.norm(sparse_points - center, axis=1)
            depths.append(dists)

        all_depths = np.concatenate(depths)
        lo = np.percentile(all_depths, percentile[0])
        hi = np.percentile(all_depths, percentile[1])

        # Add margin
        span = hi - lo
        min_d = max(0.01, lo - margin * span)
        max_d = hi + margin * span

        logger.info(f"Estimated depth range: [{min_d:.2f}, {max_d:.2f}]")
        return float(min_d), float(max_d)

    @staticmethod
    def build_pairwise_view_list(
        images: Dict[int, object],
        num_src_views: int = 4,
        min_common_points: int = 50,
    ) -> Dict[int, List[int]]:
        """
        Build a list of source views for each reference view based on
        shared 3D point observations.

        Args:
            images: COLMAP Image objects with point3d_ids.
            num_src_views: Number of source views per reference.
            min_common_points: Minimum common 3D points to consider a pair.

        Returns:
            Dict: ref_image_id -> [src_image_id_1, src_image_id_2, ...]
        """
        # Build image-to-points mapping
        img_to_pts = {}
        for img_id, img_data in images.items():
            valid = img_data.point3d_ids > 0
            img_to_pts[img_id] = set(img_data.point3d_ids[valid])

        pairs = defaultdict(list)
        img_ids = sorted(img_to_pts.keys())

        for i, ref_id in enumerate(img_ids):
            ref_pts = img_to_pts[ref_id]
            scores = []

            for src_id in img_ids:
                if src_id == ref_id:
                    continue
                common = len(ref_pts & img_to_pts[src_id])
                if common >= min_common_points:
                    scores.append((common, src_id))

            # Sort by number of common points (descending)
            scores.sort(key=lambda x: x[0], reverse=True)
            pairs[ref_id] = [s[1] for s in scores[:num_src_views]]

        return dict(pairs)
