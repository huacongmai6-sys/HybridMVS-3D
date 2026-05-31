"""
Main reconstruction pipeline.

Orchestrates the complete hybrid 3D reconstruction workflow:
  1. COLMAP SfM → camera poses + sparse point cloud
  2. Deep learning MVS → dense depth maps
  3. Depth map fusion → dense point cloud

Usage:
    from hybridmvs.pipeline import HybridReconstructionPipeline

    pipeline = HybridReconstructionPipeline(workspace_dir="./output")
    result = pipeline.run(image_dir="./images")
    pipeline.save_result(result, format="ply")
"""

import os
import time
import json
import logging
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple

import torch
import numpy as np
import cv2

from .colmap_wrapper import ColmapEngine, load_colmap_model
from .mvs_network import MVSInference
from .mvs_network.inference import MVSConfig
from .fusion import FormatConverter, DenseFusion

logger = logging.getLogger(__name__)


class HybridReconstructionPipeline:
    """
    End-to-end hybrid 3D reconstruction pipeline.

    Combines COLMAP's robust SfM with deep learning MVS for
    high-quality dense point cloud generation.
    """

    def __init__(
        self,
        workspace_dir: str = "./workspace",
        colmap_binary: Optional[str] = None,
        mvs_config: Optional[MVSConfig] = None,
        image_size: Tuple[int, int] = (640, 512),
        min_depth: float = 0.5,
        max_depth: float = 100.0,
        num_views: int = 5,
        use_gpu: bool = True,
        gpu_index: int = 0,
        max_image_dim: int = 2000,
        checkpoint_path: Optional[str] = None,
        use_colmap_dense: bool = True,
    ):
        """
        Args:
            workspace_dir: Working directory for intermediate files.
            colmap_binary: Path to COLMAP executable.
            use_colmap_dense: Use COLMAP's PatchMatch for dense (True) or MVS network (False).
            mvs_config: MVS network configuration.
            image_size: (width, height) for network input.
            min_depth: Minimum scene depth.
            max_depth: Maximum scene depth.
            num_views: Number of views for MVS (1 ref + N-1 src).
            use_gpu: Enable GPU acceleration.
            gpu_index: GPU device index.
            max_image_dim: Auto-resize images so longest edge ≤ this (default 2000).
            checkpoint_path: Path to pretrained model weights.
        """
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.image_size = image_size
        self.min_depth = min_depth
        self.max_depth = max_depth
        self.num_views = num_views
        self.use_gpu = use_gpu
        self.max_image_dim = max_image_dim
        self.checkpoint_path = checkpoint_path
        self.use_colmap_dense = use_colmap_dense

        os.makedirs(self.workspace_dir, exist_ok=True)

        # Initialize sub-modules
        logger.info("Initializing COLMAP engine...")
        self.colmap = ColmapEngine(
            workspace_dir=os.path.join(workspace_dir, "colmap"),
            colmap_binary=colmap_binary,
            gpu_index=gpu_index,
        )

        logger.info("Initializing MVS inference engine...")
        if mvs_config is None:
            ckpt = self.checkpoint_path
            if ckpt and not os.path.isfile(ckpt):
                logger.warning(f"Checkpoint not found: {ckpt}")
                ckpt = None
            mvs_config = MVSConfig(
                model_type="casmvsnet",
                num_views=num_views,
                min_depth=min_depth,
                max_depth=max_depth,
                img_height=image_size[1],
                img_width=image_size[0],
                device="cuda" if use_gpu else "cpu",
                checkpoint_path=ckpt,
            )
        self.mvs_config = mvs_config
        self.mvs_inference = MVSInference(mvs_config)

        self.dense_fusion = DenseFusion(
            consistency_threshold=0.01,
            min_views=3,
        )

        logger.info("HybridReconstructionPipeline initialized")

    def _resize_images(self, image_dir: str) -> str:
        """
        Resize large images to max_image_dim and save to a temp directory.

        Returns:
            Path to the resized image directory (same as input if no resizing needed).
        """
        import glob

        exts = ("*.jpg", "*.jpeg", "*.png", "*.tiff", "*.tif", "*.bmp")
        image_paths = []
        for ext in exts:
            image_paths.extend(glob.glob(os.path.join(image_dir, ext)))
            image_paths.extend(glob.glob(os.path.join(image_dir, ext.upper())))

        if not image_paths:
            return image_dir

        # Check if any image exceeds the limit
        need_resize = False
        for p in image_paths:
            img = cv2.imread(p)
            if img is None:
                continue
            h, w = img.shape[:2]
            if max(h, w) > self.max_image_dim:
                need_resize = True
                break

        if not need_resize:
            logger.info(f"All images within {self.max_image_dim}px, no resizing needed")
            return image_dir

        # Resize to temp dir
        resized_dir = os.path.join(self.workspace_dir, "resized_images")
        os.makedirs(resized_dir, exist_ok=True)

        count = 0
        for p in image_paths:
            img = cv2.imread(p)
            if img is None:
                continue
            h, w = img.shape[:2]
            longest = max(h, w)
            if longest > self.max_image_dim:
                scale = self.max_image_dim / longest
                new_w = int(w * scale)
                new_h = int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
                count += 1

            name = os.path.basename(p)
            cv2.imwrite(os.path.join(resized_dir, name), img)

        logger.info(f"Resized {count}/{len(image_paths)} images (max dim={self.max_image_dim}px)")
        return resized_dir

    def run(
        self,
        image_dir: str,
        quality: str = "high",
        depth_min: Optional[float] = None,
        depth_max: Optional[float] = None,
        progress_callback: Optional[callable] = None,
    ) -> Dict:
        """
        Run the complete reconstruction pipeline.

        Args:
            image_dir: Directory containing input multi-view images.
            quality: COLMAP feature quality ("low", "medium", "high", "extreme").
            depth_min: Override min depth.
            depth_max: Override max depth.
            progress_callback: Optional callback(stage, percent) for progress updates.

        Returns:
            Dict with:
              - 'dense_points': [N, 6] dense point cloud (x, y, z, r, g, b).
              - 'sparse_points': [N, 6] sparse point cloud from COLMAP.
              - 'cameras': Camera intrinsics dict.
              - 'images': Image pose dict.
              - 'depth_maps': Per-view depth maps.
              - 'stats': Timing and quality statistics.
        """
        start_time = time.time()
        stats = {}
        # Auto-resize large images
        image_dir = self._resize_images(image_dir)

        # ── Stage 1: COLMAP SfM ──────────────────────────────────────
        if progress_callback:
            progress_callback("sfm_extract_features", 0)
        logger.info("="*60)
        logger.info("Stage 1/4: COLMAP Sparse Reconstruction (SfM)")
        logger.info("="*60)

        os.makedirs(self.workspace_dir, exist_ok=True)

        t0 = time.time()
        sparse_dir = self.colmap.run_full_sfm(image_dir, quality=quality)
        cameras, images, points3d = load_colmap_model(sparse_dir)
        stats['sfm_time'] = time.time() - t0
        stats['num_registered_images'] = len(images)
        stats['num_sparse_points'] = len(points3d)

        logger.info(f"SfM complete: {len(images)} images registered, "
                     f"{len(points3d)} sparse points, "
                     f"{stats['sfm_time']:.1f}s")

        # Extract sparse point cloud as numpy array
        sparse_points = np.array([[p.xyz[0], p.xyz[1], p.xyz[2],
                                    p.rgb[0] / 255.0, p.rgb[1] / 255.0, p.rgb[2] / 255.0]
                                   for p in points3d.values()])

        if progress_callback:
            progress_callback("sfm_complete", 25)

        # ── Stage 2: Data Conversion ─────────────────────────────────
        if progress_callback:
            progress_callback("convert", 25)
        logger.info("="*60)
        logger.info("Stage 2/4: Format Conversion")
        logger.info("="*60)

        t0 = time.time()
        converter = FormatConverter()
        img_list, K_list, E_list, img_names = converter.colmap_to_mvs_input(
            cameras, images, image_dir,
            target_height=self.image_size[1],
            target_width=self.image_size[0],
        )

        # Estimate depth range from sparse points if not user-specified
        if depth_min is None or depth_max is None:
            camera_centers = np.array([E[:3, 3] for E in E_list])
            est_dmin, est_dmax = converter.compute_depth_range(
                sparse_points[:, :3], camera_centers,
            )
            if depth_min is None:
                depth_min = est_dmin
            if depth_max is None:
                depth_max = est_dmax

        # Fallback to defaults if still None
        dmin = depth_min if depth_min is not None else self.min_depth
        dmax = depth_max if depth_max is not None else self.max_depth

        stats['conversion_time'] = time.time() - t0
        stats['estimated_depth_range'] = (float(dmin), float(dmax))

        logger.info(f"Converted {len(img_list)} images for MVS, "
                     f"depth range: [{dmin:.2f}, {dmax:.2f}]")

        if progress_callback:
            progress_callback("conversion_complete", 30)

        # ── COLMAP Dense Path (skip MVS network) ────────────────────
        if self.use_colmap_dense:
            if progress_callback:
                progress_callback("undistort", 30)
            logger.info("="*60)
            logger.info("Stage 3/4: COLMAP Dense Reconstruction (PatchMatch)")
            logger.info("="*60)

            t0 = time.time()

            # Step 1: Undistort (use smaller size for dense: 1200px)
            dense_size = min(self.max_image_dim, 1200)
            self.colmap.image_undistorter(image_dir, "0", dense_size)
            if progress_callback:
                progress_callback("patch_match", 40)

            # Step 2: PatchMatch stereo (slowest)
            output_path = os.path.join(self.colmap.dense_dir, "fused.ply")
            self.colmap.patch_match_stereo()
            if progress_callback:
                progress_callback("stereo_fusion", 80)

            # Step 3: Fusion
            self.colmap.stereo_fusion(output_path)
            stats['dense_time'] = time.time() - t0

            # Load fused point cloud
            dense_points = DenseFusion.load_point_cloud(output_path)
            depth_maps = []
            conf_maps = []

            stats['num_dense_points'] = len(dense_points) if len(dense_points.shape) > 0 else 0
            stats['total_time'] = time.time() - start_time

            logger.info(f"Dense complete: {stats.get('num_dense_points', 0)} points, "
                         f"{stats['dense_time']:.1f}s")
            logger.info(f"Total pipeline time: {stats['total_time']:.1f}s")

            if progress_callback:
                progress_callback("complete", 100)

            return {
                'dense_points': dense_points,
                'sparse_points': sparse_points,
                'cameras': cameras,
                'images': images,
                'depth_maps': depth_maps,
                'confidence_maps': conf_maps,
                'image_names': img_names,
                'stats': stats,
            }

        # ── Stage 3: Deep Learning MVS ───────────────────────────────
        if progress_callback:
            progress_callback("mvs_depth", 30)
        logger.info("="*60)
        logger.info("Stage 3/4: Deep Learning MVS Depth Estimation")
        logger.info("="*60)

        t0 = time.time()
        depth_maps = []
        conf_maps = []

        total_views = len(img_list)
        for i in range(total_views):
            pct = 30 + int(35 * (i + 1) / total_views)
            if progress_callback:
                progress_callback("mvs_depth", pct)

            depth, conf = self.mvs_inference.run(
                img_list, K_list, E_list, ref_idx=i,
                depth_min=dmin, depth_max=dmax,
                original_size=None,  # keep network resolution
            )
            depth_maps.append(depth)
            conf_maps.append(conf)

        stats['mvs_time'] = time.time() - t0
        stats['num_depth_maps'] = len(depth_maps)
        stats['avg_confidence'] = float(np.mean([c.mean() for c in conf_maps]))

        logger.info(f"MVS complete: {len(depth_maps)} depth maps, "
                     f"avg confidence: {stats['avg_confidence']:.3f}, "
                     f"{stats['mvs_time']:.1f}s")

        if progress_callback:
            progress_callback("mvs_complete", 65)

        # ── Stage 4: Dense Fusion ────────────────────────────────────
        if progress_callback:
            progress_callback("fusion", 65)
        logger.info("="*60)
        logger.info("Stage 4/4: Dense Point Cloud Fusion")
        logger.info("="*60)

        t0 = time.time()

        # Load full-res images for color
        full_images = []
        for name in img_names:
            img_path = os.path.join(image_dir, name)
            if os.path.isfile(img_path):
                img = cv2.imread(img_path)
                if img is not None:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            else:
                img = None
            full_images.append(img)

        # Fuse depth maps with built-in DTU-style multi-view consistency filter.
        # Each pixel is checked against all other views BEFORE unprojection.
        # Confidence pre-filter disabled (set to 0) — the model produces low
        # confidence on real photos (near-uniform prob distribution). Rely on
        # geometric consistency filter (min_views=3) for noise removal instead.
        dense_points = self.dense_fusion.fuse_depth_maps(
            depth_maps, K_list, E_list,
            images=full_images,
            confidence_maps=conf_maps,
            min_confidence=0.0,
        )

        # Downsample
        if len(dense_points) > 0:
            dense_points = self.dense_fusion.downsample(dense_points)

        stats['fusion_time'] = time.time() - t0
        stats['num_dense_points'] = len(dense_points)
        stats['total_time'] = time.time() - start_time

        logger.info(f"Fusion complete: {len(dense_points)} points, "
                     f"{stats['fusion_time']:.1f}s")
        logger.info(f"Total pipeline time: {stats['total_time']:.1f}s")

        if progress_callback:
            progress_callback("complete", 100)

        return {
            'dense_points': dense_points,
            'sparse_points': sparse_points,
            'cameras': cameras,
            'images': images,
            'depth_maps': depth_maps,
            'confidence_maps': conf_maps,
            'image_names': img_names,
            'stats': stats,
        }

    def save_result(
        self,
        result: Dict,
        output_dir: str = "./output",
        formats: List[str] = None,
    ) -> Dict[str, str]:
        """
        Save reconstruction results to disk.

        Args:
            result: Pipeline output dict.
            output_dir: Output directory.
            formats: List of formats for point cloud ("ply", "obj", "xyz").

        Returns:
            Dict mapping format to file path.
        """
        if formats is None:
            formats = ["ply", "obj"]

        os.makedirs(output_dir, exist_ok=True)
        paths = {}

        # Save dense point cloud
        dense = result['dense_points']
        for fmt in formats:
            path = os.path.join(output_dir, f"dense_cloud.{fmt}")
            paths[fmt] = self.dense_fusion.save_point_cloud(dense, path, fmt=fmt)

        # Save sparse point cloud
        sparse = result['sparse_points']
        sparse_path = os.path.join(output_dir, "sparse_cloud.ply")
        paths['sparse'] = self.dense_fusion.save_point_cloud(
            sparse, sparse_path, fmt="ply"
        )

        # Save depth maps
        depth_dir = os.path.join(output_dir, "depth_maps")
        FormatConverter.save_depth_maps(
            result['depth_maps'], depth_dir,
            image_names=result.get('image_names'),
            fmt="npy",
        )

        # Save stats
        stats_path = os.path.join(output_dir, "reconstruction_stats.json")
        with open(stats_path, 'w') as f:
            json.dump(result['stats'], f, indent=2, default=str)
        paths['stats'] = stats_path

        # Save camera info
        cam_path = os.path.join(output_dir, "cameras.json")
        cam_info = {}
        for cam_id, cam in result['cameras'].items():
            cam_info[str(cam_id)] = {
                'model': cam.model,
                'width': cam.width,
                'height': cam.height,
                'params': cam.params.tolist(),
            }
        with open(cam_path, 'w') as f:
            json.dump(cam_info, f, indent=2)
        paths['cameras'] = cam_path

        logger.info(f"Results saved to {output_dir}")
        return paths


def run_pipeline_cli(
    image_dir: str,
    output_dir: str = "./output",
    quality: str = "high",
    model_type: str = "casmvsnet",
    depth_min: Optional[float] = None,
    depth_max: Optional[float] = None,
) -> Dict:
    """
    Convenience function to run the pipeline from command line.

    Args:
        image_dir: Input image directory.
        output_dir: Output directory.
        quality: COLMAP quality.
        model_type: MVS model type.
        depth_min, depth_max: Depth range override.

    Returns:
        Pipeline result dict.
    """
    logging.basicConfig(level=logging.INFO)
    logger.info(f"HybridMVS Pipeline")
    logger.info(f"  Images: {image_dir}")
    logger.info(f"  Output: {output_dir}")
    logger.info(f"  Model:  {model_type}")
    logger.info(f"  GPU:    {'available' if torch.cuda.is_available() else 'not available'}")

    mvs_cfg = MVSConfig(
        model_type=model_type,
        num_views=5,
        min_depth=depth_min or 0.5,
        max_depth=depth_max or 100.0,
        img_height=512,
        img_width=640,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )

    pipeline = HybridReconstructionPipeline(
        workspace_dir=os.path.join(output_dir, "workspace"),
        mvs_config=mvs_cfg,
    )

    result = pipeline.run(image_dir, quality=quality,
                          depth_min=depth_min, depth_max=depth_max)

    pipeline.save_result(result, output_dir)

    logger.info("Pipeline complete!")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HybridMVS Reconstruction Pipeline")
    parser.add_argument("--image_dir", required=True, help="Input image directory")
    parser.add_argument("--output_dir", default="./output", help="Output directory")
    parser.add_argument("--quality", default="high",
                        choices=["low", "medium", "high", "extreme"])
    parser.add_argument("--model", default="casmvsnet",
                        choices=["mvsnet", "casmvsnet"])
    parser.add_argument("--depth_min", type=float, default=None)
    parser.add_argument("--depth_max", type=float, default=None)

    args = parser.parse_args()

    import torch
    run_pipeline_cli(
        image_dir=args.image_dir,
        output_dir=args.output_dir,
        quality=args.quality,
        model_type=args.model,
        depth_min=args.depth_min,
        depth_max=args.depth_max,
    )
