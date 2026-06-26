"""
COLMAP engine wrapper.

Manages COLMAP SfM pipeline via subprocess calls to the COLMAP executable.
Provides automatic download/installation of COLMAP if not found.
"""

import os
import sys
import json
import shutil
import zipfile
import logging
import subprocess
import urllib.request
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict

from .utils import (
    read_cameras, read_images, read_points3d,
    write_cameras, write_images, write_points3d,
    Camera, Image, Point3D,
)

logger = logging.getLogger(__name__)

# Known COLMAP download URLs
COLMAP_URLS = {
    "windows": "https://github.com/colmap/colmap/releases/download/4.0.4/colmap-x64-windows-cuda.zip",
    # Linux: prefer system package manager (apt install colmap)
    # macOS: brew install colmap
}


class ColmapEngine:
    """
    Wrapper around COLMAP for camera pose estimation and sparse reconstruction.

    Usage:
        engine = ColmapEngine(workspace_dir="/path/to/workspace")
        engine.run(image_dir="/path/to/images")
    """

    def __init__(
        self,
        workspace_dir: str,
        colmap_binary: Optional[str] = None,
        camera_model: str = "SIMPLE_RADIAL",
        single_camera: bool = True,
        gpu_index: int = 0,
    ):
        """
        Args:
            workspace_dir: Directory for COLMAP working files and output.
            colmap_binary: Path to COLMAP executable. Auto-detects if None.
            camera_model: Camera intrinsic model (default: SIMPLE_RADIAL).
            single_camera: Use same camera intrinsics for all images.
            gpu_index: GPU device index for feature extraction/matching.
        """
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.database_path = os.path.join(self.workspace_dir, "database.db")
        self.sparse_dir = os.path.join(self.workspace_dir, "sparse")
        self.dense_dir = os.path.join(self.workspace_dir, "dense")
        self.camera_model = camera_model
        self.single_camera = single_camera
        self.gpu_index = gpu_index
        self.colmap_binary = colmap_binary or self._find_colmap()
        self._is_v4 = self._detect_v4()

    def _detect_v4(self) -> bool:
        """Try v4 option naming; if it works, return True, else False."""
        # Run a quick no-op-ish command that probes the option namespace.
        # COLMAP 4.x renamed FeatureExtraction → SiftExtraction, FeatureMatching → SiftMatching.
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            try:
                result = subprocess.run(
                    [self.colmap_binary, "feature_extractor",
                     "--database_path", db_path,
                     "--image_path", tmpdir,
                     "--SiftExtraction.use_gpu", "1"],
                    capture_output=True, text=True, timeout=15,
                )
                # "unrecognised option" means v3; any other error (e.g. no images) means v4 accepted the option
                if "unrecognised option" in (result.stderr or ""):
                    return False
                return True
            except Exception:
                return False

    def _find_colmap(self) -> str:
        """Locate COLMAP executable, downloading if necessary."""
        # Check PATH first (works on Linux/macOS, and Windows if in PATH)
        result = shutil.which("colmap")
        if result:
            logger.info(f"Found COLMAP in PATH: {result}")
            return result

        # Platform-specific common install locations
        if sys.platform == "win32":
            common_paths = [
                os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "COLMAP", "bin", "colmap.exe"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "COLMAP", "bin", "colmap.exe"),
                os.path.expanduser("~\\colmap\\bin\\colmap.exe"),
            ]
        else:
            # Linux / macOS common locations
            common_paths = [
                "/usr/bin/colmap",
                "/usr/local/bin/colmap",
                os.path.expanduser("~/colmap/bin/colmap"),
                os.path.expanduser("~/.local/bin/colmap"),
            ]

        for p in common_paths:
            if os.path.isfile(p):
                logger.info(f"Found COLMAP at: {p}")
                return p

        # Auto-download (Windows only; Linux/macOS should use package manager)
        if sys.platform == "win32":
            logger.info("COLMAP not found, attempting auto-download...")
            return self._download_colmap()
        else:
            raise FileNotFoundError(
                "COLMAP not found. Install it via your package manager:\n"
                "  Linux:   sudo apt install colmap\n"
                "  macOS:   brew install colmap\n"
                "Or set the COLMAP_BINARY environment variable to the colmap executable path."
            )

    def _download_colmap(self) -> str:
        """Download COLMAP (Windows only — auto-downloads the prebuilt binary)."""
        colmap_dir = os.path.join(os.path.expanduser("~"), "colmap")
        os.makedirs(colmap_dir, exist_ok=True)

        url = COLMAP_URLS["windows"]
        zip_path = os.path.join(colmap_dir, "colmap.zip")

        logger.info(f"Downloading COLMAP from {url} ...")
        urllib.request.urlretrieve(url, zip_path)

        logger.info(f"Extracting to {colmap_dir} ...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(colmap_dir)

        os.remove(zip_path)

        # Find the colmap binary
        binary_name = "colmap.exe" if sys.platform == "win32" else "colmap"
        for root, dirs, files in os.walk(colmap_dir):
            if binary_name in files:
                exe_path = os.path.join(root, binary_name)
                logger.info(f"COLMAP installed to: {exe_path}")
                return exe_path

        raise FileNotFoundError(f"Could not find {binary_name} after extraction")

    def _run_command(self, *args, allow_failure: bool = False) -> subprocess.CompletedProcess:
        """Run a COLMAP command with proper error handling."""
        cmd = [self.colmap_binary] + list(args)
        msg = f"Running: {' '.join(cmd)}"
        if len(msg) > 200:
            msg = msg[:200] + "..."
        logger.info(msg)

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            msg = result.stderr.strip()
            # Truncate long error messages for logging
            short_msg = msg[:500] + "..." if len(msg) > 500 else msg
            if allow_failure:
                logger.warning(f"COLMAP command failed (non-fatal): {short_msg}")
            else:
                logger.error(f"COLMAP command failed: {short_msg}")
                raise RuntimeError(f"COLMAP error: {msg}")

        return result

    def extract_features(self, image_dir: str, quality: str = "high") -> None:
        """
        Extract SIFT features from images.

        Args:
            image_dir: Directory containing input images.
            quality: Feature extraction quality ("low", "medium", "high", "extreme").
        """
        os.makedirs(self.workspace_dir, exist_ok=True)

        if self._is_v4:
            # COLMAP 4.x renamed FeatureExtraction → SiftExtraction
            self._run_command(
                "feature_extractor",
                "--database_path", self.database_path,
                "--image_path", image_dir,
                "--ImageReader.single_camera", "1" if self.single_camera else "0",
                "--ImageReader.camera_model", self.camera_model,
                "--SiftExtraction.use_gpu", "1",
                "--SiftExtraction.gpu_index", str(self.gpu_index),
            )
        else:
            self._run_command(
                "feature_extractor",
                "--database_path", self.database_path,
                "--image_path", image_dir,
                "--ImageReader.single_camera", "1" if self.single_camera else "0",
                "--ImageReader.camera_model", self.camera_model,
                "--FeatureExtraction.use_gpu", "1",
                "--FeatureExtraction.gpu_index", str(self.gpu_index),
            )

    def match_features(self, match_type: str = "exhaustive") -> None:
        """
        Match features between image pairs.

        Args:
            match_type: Matching strategy ("exhaustive", "sequential", "spatial", "vocab_tree").
        """
        if self._is_v4:
            gpu_block = "SiftMatching"
        else:
            gpu_block = "FeatureMatching"

        if match_type == "exhaustive":
            self._run_command(
                "exhaustive_matcher",
                "--database_path", self.database_path,
                f"--{gpu_block}.use_gpu", "1",
                f"--{gpu_block}.gpu_index", str(self.gpu_index),
            )
        elif match_type == "sequential":
            self._run_command(
                "sequential_matcher",
                "--database_path", self.database_path,
                f"--{gpu_block}.use_gpu", "1",
            )
        elif match_type == "vocab_tree":
            self._run_command(
                "vocab_tree_matcher",
                "--database_path", self.database_path,
                f"--{gpu_block}.use_gpu", "1",
            )
        else:
            raise ValueError(f"Unknown match type: {match_type}")

    def run_sparse_reconstruction(self, image_dir: str) -> str:
        """Run sparse SfM reconstruction (mapper). Returns model dir path."""
        os.makedirs(self.sparse_dir, exist_ok=True)

        result = self._run_command(
            "mapper",
            "--database_path", self.database_path,
            "--image_path", image_dir,
            "--output_path", self.sparse_dir,
            allow_failure=True,
        )

        # COLMAP 4.x outputs .bin format by default. Convert to .txt for our parser.
        sparse_outputs = sorted(Path(self.sparse_dir).glob("[0-9]*"))
        if sparse_outputs:
            model_dir = str(sparse_outputs[0])
            if os.path.isfile(os.path.join(model_dir, "cameras.bin")):
                self._run_command(
                    "model_converter",
                    "--input_path", model_dir,
                    "--output_path", model_dir,
                    "--output_type", "TXT",
                )
            return model_dir

        # No reconstruction produced
        stderr = (result.stderr or "").strip()
        if "No good initial image pair" in stderr:
            raise RuntimeError(
                "COLMAP could not find enough matching features between images. "
                "This usually means:\n"
                "  1. Images don't have enough overlap (try more viewpoints)\n"
                "  2. Scene lacks texture (avoid blank walls, solid colors)\n"
                "  3. Images are too blurry or poorly lit"
            )
        return ""

    def run_full_sfm(self, image_dir: str, quality: str = "high") -> str:
        """
        Run complete SfM pipeline: feature extraction + matching + sparse reconstruction.

        Args:
            image_dir: Directory containing input images.
            quality: Feature extraction quality.

        Returns:
            Path to the sparse reconstruction output directory (subdir of sparse_dir).
        """
        self.extract_features(image_dir, quality=quality)
        self.match_features(match_type="exhaustive")
        result_dir = self.run_sparse_reconstruction(image_dir)

        # Find the output directory (COLMAP creates a numbered subdir)
        sparse_outputs = sorted(Path(self.sparse_dir).glob("[0-9]*"))
        if not sparse_outputs or not result_dir:
            raise RuntimeError(f"No sparse reconstruction output found in {self.sparse_dir}")

        result_dir = str(sparse_outputs[0])
        logger.info(f"SfM reconstruction complete: {result_dir}")
        return result_dir

    def load_sparse_model(self, sparse_subdir: str = "0") -> tuple:
        """Load a sparse COLMAP model from a numbered subdirectory of sparse_dir."""
        model_dir = os.path.join(self.sparse_dir, sparse_subdir)
        if not os.path.isdir(model_dir):
            raise FileNotFoundError(f"Model directory not found: {model_dir}")
        return read_cameras(model_dir), read_images(model_dir), read_points3d(model_dir)

    def get_camera_poses(self, sparse_subdir: str = "0") -> Dict[int, np.ndarray]:
        """
        Get camera-to-world 4x4 matrices for all registered images.

        Returns:
            Dict of image_id -> 4x4 camera-to-world matrix.
        """
        _, images, _ = self.load_sparse_model(sparse_subdir)
        return {img_id: img.camera_to_world for img_id, img in images.items()}

    def get_intrinsics(self, sparse_subdir: str = "0") -> Dict[int, np.ndarray]:
        """
        Get 3x3 intrinsic matrices for all cameras.

        Returns:
            Dict of camera_id -> 3x3 intrinsic matrix.
        """
        cameras, _, _ = self.load_sparse_model(sparse_subdir)
        return {cam_id: cam.K for cam_id, cam in cameras.items()}

    def get_image_list(self, sparse_subdir: str = "0") -> List[str]:
        """Get list of registered image filenames sorted by image_id."""
        _, images, _ = self.load_sparse_model(sparse_subdir)
        return [img.name for _, img in sorted(images.items(), key=lambda x: x[0])]

    def image_undistorter(
        self, image_dir: str, sparse_subdir: str = "0",
        max_image_size: int = 2000
    ) -> str:
        """
        Run COLMAP image_undistorter to prepare for dense reconstruction.

        Returns:
            Path to the undistorted output directory.
        """
        model_dir = os.path.join(self.sparse_dir, sparse_subdir)
        os.makedirs(self.dense_dir, exist_ok=True)

        self._run_command(
            "image_undistorter",
            "--image_path", image_dir,
            "--input_path", model_dir,
            "--output_path", self.dense_dir,
            "--output_type", "COLMAP",
            "--max_image_size", str(max_image_size),
        )
        return os.path.join(self.dense_dir, "sparse")

    def patch_match_stereo(self, stereo_dir: str = None) -> None:
        """Run COLMAP patch match stereo for dense depth estimation."""
        if stereo_dir is None:
            stereo_dir = self.dense_dir
        self._run_command(
            "patch_match_stereo",
            "--workspace_path", stereo_dir,
            "--workspace_format", "COLMAP",
            "--PatchMatchStereo.geom_consistency", "true",
            "--PatchMatchStereo.gpu_index", str(self.gpu_index),
            "--PatchMatchStereo.max_image_size", "1200",
            "--PatchMatchStereo.window_radius", "3",
            "--PatchMatchStereo.window_step", "1",
            "--PatchMatchStereo.num_iterations", "3",
            "--PatchMatchStereo.num_samples", "7",
        )

    def stereo_fusion(self, output_path: str, stereo_dir: str = None) -> str:
        """Fuse depth maps into a dense point cloud."""
        if stereo_dir is None:
            stereo_dir = self.dense_dir
        self._run_command(
            "stereo_fusion",
            "--workspace_path", stereo_dir,
            "--workspace_format", "COLMAP",
            "--input_type", "geometric",
            "--output_path", output_path,
        )
        return output_path

    def run_dense_reconstruction(
        self, image_dir: str, sparse_subdir: str = "0",
        max_image_size: int = 2000, output_path: str = None,
    ) -> str:
        """
        Run COLMAP's dense reconstruction pipeline:
        image_undistorter → patch_match_stereo → stereo_fusion.

        Returns path to the fused PLY point cloud.
        """
        if output_path is None:
            output_path = os.path.join(self.dense_dir, "fused.ply")

        # Step 1: Undistort images
        logger.info("Dense: Undistorting images...")
        self.image_undistorter(image_dir, sparse_subdir, max_image_size)

        # Step 2: PatchMatch stereo
        logger.info("Dense: Running PatchMatch stereo...")
        self.patch_match_stereo()

        # Step 3: Stereo fusion
        logger.info("Dense: Fusing depth maps...")
        self.stereo_fusion(output_path)

        return output_path
