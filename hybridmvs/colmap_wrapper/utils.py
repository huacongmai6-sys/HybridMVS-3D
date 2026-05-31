"""
COLMAP data format utilities.

COLMAP stores models as text files: cameras.txt, images.txt, points3D.txt
This module provides read/write functions for these files.

COLMAP text format reference:
- cameras.txt: CAMERA_ID, MODEL, WIDTH, HEIGHT, params[]
- images.txt: IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME, POINTS2D[]...
- points3D.txt: POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[]...
"""

import os
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


# Camera models used by COLMAP
CAMERA_MODEL_IDS = {
    "SIMPLE_PINHOLE": 0,
    "PINHOLE": 1,
    "SIMPLE_RADIAL": 2,
    "RADIAL": 3,
    "OPENCV": 4,
    "OPENCV_FISHEYE": 5,
    "FULL_OPENCV": 6,
    "FOV": 7,
    "SIMPLE_RADIAL_FISHEYE": 8,
    "RADIAL_FISHEYE": 9,
    "THIN_PRISM_FISHEYE": 10,
}

CAMERA_MODEL_NAMES = {v: k for k, v in CAMERA_MODEL_IDS.items()}

CAMERA_MODEL_PARAMS = {
    "SIMPLE_PINHOLE": 3,  # f, cx, cy
    "PINHOLE": 4,         # fx, fy, cx, cy
    "SIMPLE_RADIAL": 4,   # f, cx, cy, k
    "RADIAL": 5,          # f, cx, cy, k1, k2
    "OPENCV": 8,          # fx, fy, cx, cy, k1, k2, p1, p2
    "OPENCV_FISHEYE": 8,  # fx, fy, cx, cy, k1, k2, k3, k4
    "FULL_OPENCV": 12,    # fx, fy, cx, cy, k1, k2, p1, p2, k3, k4, k5, k6
    "FOV": 5,             # fx, fy, cx, cy, omega
    "SIMPLE_RADIAL_FISHEYE": 4,  # f, cx, cy, k
    "RADIAL_FISHEYE": 5,  # f, cx, cy, k1, k2
    "THIN_PRISM_FISHEYE": 12,  # fx, fy, cx, cy, k1, k2, p1, p2, k3, k4, sx1, sy1
}


@dataclass
class Camera:
    """COLMAP camera model."""
    id: int
    model: str          # e.g., "PINHOLE", "SIMPLE_RADIAL"
    width: int
    height: int
    params: np.ndarray  # camera parameters as a 1D array

    @property
    def K(self) -> np.ndarray:
        """Return 3x3 intrinsic matrix (for PINHOLE-based models)."""
        if self.model in ("SIMPLE_PINHOLE", "SIMPLE_RADIAL"):
            f, cx, cy = self.params[0], self.params[1], self.params[2]
            return np.array([[f, 0, cx], [0, f, cy], [0, 0, 1]], dtype=np.float64)
        elif self.model in ("PINHOLE", "OPENCV", "OPENCV_FISHEYE", "FULL_OPENCV", "FOV"):
            fx, fy, cx, cy = self.params[0], self.params[1], self.params[2], self.params[3]
            return np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=np.float64)
        else:
            raise ValueError(f"Unsupported camera model for K: {self.model}")


@dataclass
class Image:
    """COLMAP image (camera pose) data."""
    id: int
    qvec: np.ndarray     # [qw, qx, qy, qz] quaternion
    tvec: np.ndarray     # [tx, ty, tz] translation vector
    camera_id: int
    name: str
    xys: np.ndarray      # Nx2 array of keypoint coordinates
    point3d_ids: np.ndarray  # N array of 3D point IDs (-1 for unmatched)

    @property
    def R(self) -> np.ndarray:
        """Return 3x3 rotation matrix from quaternion."""
        return qvec2rotmat(self.qvec)

    @property
    def C(self) -> np.ndarray:
        """Return camera center in world coordinates: C = -R^T * t."""
        return -self.R.T @ self.tvec

    @property
    def world_to_camera(self) -> np.ndarray:
        """Return 4x4 world-to-camera transformation matrix."""
        P = np.eye(4, dtype=np.float64)
        P[:3, :3] = self.R
        P[:3, 3] = self.tvec
        return P

    @property
    def camera_to_world(self) -> np.ndarray:
        """Return 4x4 camera-to-world transformation matrix."""
        P = np.eye(4, dtype=np.float64)
        P[:3, :3] = self.R.T
        P[:3, 3] = -self.R.T @ self.tvec
        return P


@dataclass
class Point3D:
    """COLMAP 3D point."""
    id: int
    xyz: np.ndarray   # [x, y, z]
    rgb: np.ndarray   # [r, g, b] in [0, 255]
    error: float
    image_ids: List[int]
    point2d_idxs: List[int]


def qvec2rotmat(qvec: np.ndarray) -> np.ndarray:
    """Convert quaternion [qw, qx, qy, qz] to 3x3 rotation matrix."""
    qw, qx, qy, qz = qvec
    return np.array([
        [1 - 2*qy**2 - 2*qz**2, 2*qx*qy - 2*qz*qw,     2*qx*qz + 2*qy*qw],
        [2*qx*qy + 2*qz*qw,     1 - 2*qx**2 - 2*qz**2, 2*qy*qz - 2*qx*qw],
        [2*qx*qz - 2*qy*qw,     2*qy*qz + 2*qx*qw,     1 - 2*qx**2 - 2*qy**2],
    ], dtype=np.float64)


def rotmat2qvec(R: np.ndarray) -> np.ndarray:
    """Convert 3x3 rotation matrix to quaternion [qw, qx, qy, qz]."""
    qw = np.sqrt(1.0 + R[0, 0] + R[1, 1] + R[2, 2]) / 2.0
    if qw > 1e-8:
        qx = (R[2, 1] - R[1, 2]) / (4.0 * qw)
        qy = (R[0, 2] - R[2, 0]) / (4.0 * qw)
        qz = (R[1, 0] - R[0, 1]) / (4.0 * qw)
    else:
        qx = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) / 2.0
        qy = np.sqrt(1.0 - R[0, 0] + R[1, 1] - R[2, 2]) / 2.0
        qz = np.sqrt(1.0 - R[0, 0] - R[1, 1] + R[2, 2]) / 2.0
    return np.array([qw, qx, qy, qz], dtype=np.float64)


def read_cameras(path: str) -> Dict[int, Camera]:
    """Read COLMAP cameras.txt. Returns dict of camera_id -> Camera.

    Handles both COLMAP 3.x (numeric model ID) and 4.x (model name string) formats.
    """
    cameras = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            camera_id = int(parts[0])
            # COLMAP 4.x uses model name string, 3.x uses numeric ID
            if parts[1].isdigit():
                model = CAMERA_MODEL_NAMES.get(int(parts[1]), "UNKNOWN")
            else:
                model = parts[1]
            width = int(parts[2])
            height = int(parts[3])
            params = np.array([float(x) for x in parts[4:]], dtype=np.float64)
            cameras[camera_id] = Camera(id=camera_id, model=model,
                                        width=width, height=height, params=params)
    return cameras


def read_images(path: str) -> Dict[int, Image]:
    """Read COLMAP images.txt. Returns dict of image_id -> Image."""
    images = {}
    with open(path, 'r') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith('#'):
            i += 1
            continue

        parts = line.split()
        image_id = int(parts[0])
        qvec = np.array([float(x) for x in parts[1:5]], dtype=np.float64)
        tvec = np.array([float(x) for x in parts[5:8]], dtype=np.float64)
        camera_id = int(parts[8])
        name = parts[9]

        # Parse 2D-3D correspondences
        points_data = parts[10:]
        n_points = len(points_data) // 3
        xys = np.zeros((n_points, 2), dtype=np.float64)
        point3d_ids = np.zeros(n_points, dtype=np.int64)
        for j in range(n_points):
            xys[j, 0] = float(points_data[3 * j])
            xys[j, 1] = float(points_data[3 * j + 1])
            point3d_ids[j] = int(points_data[3 * j + 2])

        images[image_id] = Image(
            id=image_id, qvec=qvec, tvec=tvec,
            camera_id=camera_id, name=name,
            xys=xys, point3d_ids=point3d_ids,
        )
        i += 2  # each image entry spans two lines in COLMAP text format

    return images


def read_points3d(path: str) -> Dict[int, Point3D]:
    """Read COLMAP points3D.txt. Returns dict of point_id -> Point3D."""
    points = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            point_id = int(parts[0])
            xyz = np.array([float(parts[1]), float(parts[2]), float(parts[3])])
            rgb = np.array([int(parts[4]), int(parts[5]), int(parts[6])])
            error = float(parts[7])
            track_data = parts[8:]
            n_track = len(track_data) // 2
            image_ids = [int(track_data[2 * j]) for j in range(n_track)]
            point2d_idxs = [int(track_data[2 * j + 1]) for j in range(n_track)]
            points[point_id] = Point3D(
                id=point_id, xyz=xyz, rgb=rgb, error=error,
                image_ids=image_ids, point2d_idxs=point2d_idxs,
            )
    return points


def write_cameras(cameras: Dict[int, Camera], path: str) -> None:
    """Write cameras to COLMAP cameras.txt format (model name string for COLMAP 4.x)."""
    with open(path, 'w') as f:
        f.write("# Camera list with one line of data per camera:\n")
        f.write("#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
        f.write(f"# Number of cameras: {len(cameras)}\n")
        for cam in cameras.values():
            params_str = " ".join(str(p) for p in cam.params)
            f.write(f"{cam.id} {cam.model} {cam.width} {cam.height} {params_str}\n")


def write_images(images: Dict[int, Image], path: str) -> None:
    """Write images to COLMAP images.txt format."""
    with open(path, 'w') as f:
        f.write("# Image list with two lines of data per image:\n")
        f.write("#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        f.write("#   POINTS2D[] as (X, Y, POINT3D_ID)\n")
        f.write(f"# Number of images: {len(images)}, mean observations per image: ...\n")
        for img in sorted(images.values(), key=lambda x: x.id):
            qstr = " ".join(str(q) for q in img.qvec)
            tstr = " ".join(str(t) for t in img.tvec)
            f.write(f"{img.id} {qstr} {tstr} {img.camera_id} {img.name}\n")
            pts_str = " ".join(
                f"{img.xys[j, 0]} {img.xys[j, 1]} {img.point3d_ids[j]}"
                for j in range(len(img.point3d_ids))
            )
            f.write(f"{pts_str}\n")


def write_points3d(points: Dict[int, Point3D], path: str) -> None:
    """Write 3D points to COLMAP points3D.txt format."""
    with open(path, 'w') as f:
        f.write("# 3D point list with one line of data per point:\n")
        f.write("#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
        f.write(f"# Number of points: {len(points)}\n")
        for pt in sorted(points.values(), key=lambda x: x.id):
            track_str = " ".join(
                f"{pt.image_ids[j]} {pt.point2d_idxs[j]}"
                for j in range(len(pt.image_ids))
            )
            f.write(f"{pt.id} {pt.xyz[0]} {pt.xyz[1]} {pt.xyz[2]} "
                    f"{int(pt.rgb[0])} {int(pt.rgb[1])} {int(pt.rgb[2])} "
                    f"{pt.error} {track_str}\n")


def load_colmap_model(model_dir: str) -> Tuple[Dict[int, Camera], Dict[int, Image], Dict[int, Point3D]]:
    """Load a complete COLMAP model from a directory."""
    cameras = read_cameras(os.path.join(model_dir, "cameras.txt"))
    images = read_images(os.path.join(model_dir, "images.txt"))
    points = read_points3d(os.path.join(model_dir, "points3D.txt"))
    return cameras, images, points


def save_colmap_model(
    cameras: Dict[int, Camera],
    images: Dict[int, Image],
    points: Dict[int, Point3D],
    model_dir: str,
) -> None:
    """Save a complete COLMAP model to a directory."""
    os.makedirs(model_dir, exist_ok=True)
    write_cameras(cameras, os.path.join(model_dir, "cameras.txt"))
    write_images(images, os.path.join(model_dir, "images.txt"))
    write_points3d(points, os.path.join(model_dir, "points3D.txt"))
