"""
Paper-standard point cloud comparison metrics.

Implements the CVPR/ECCV five-metric suite:
  1. Chamfer Distance (CD)
  2. Accuracy / Completeness (separated, mean + median)
  3. F-score (Precision / Recall / F1 at multiple thresholds)
  4. Outlier Ratio
  5. Normal Consistency (PCA-based, no open3d dependency)

All distance metrics share one scipy.spatial.cKDTree per point cloud
for O(N log N) efficiency.
"""

import os
import sys
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# Import PLY loader from existing fusion module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hybridmvs.fusion.dense_fusion import DenseFusion


# ═══════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════

def _load_xyz(path: str) -> np.ndarray:
    """
    Load a PLY file and extract only XYZ coordinates as [N, 3] float32.
    Reuses DenseFusion.load_point_cloud (or raw parser fallback).
    """
    pts = DenseFusion.load_point_cloud(path)
    if pts.ndim != 2 or pts.shape[0] == 0:
        raise ValueError(f"Empty or invalid point cloud: {path} ({getattr(pts, 'shape', '?')})")
    return pts[:, :3].astype(np.float64).copy()


def _subsample(points: np.ndarray, max_points: int, seed: int = 42) -> np.ndarray:
    """Randomly subsample if point count exceeds max_points."""
    n = len(points)
    if n <= max_points:
        return points
    rng = np.random.RandomState(seed)
    idx = rng.choice(n, max_points, replace=False)
    logger.info(f"Subsampled: {n} → {max_points} points")
    return points[idx]


def _compute_pairwise_metrics(
    pred: np.ndarray,   # [M, 3]
    gt: np.ndarray,     # [N, 3]
    thresholds: List[float],
    outlier_threshold: float,
    pred_normals: Optional[np.ndarray] = None,  # [M, 3]
    gt_normals: Optional[np.ndarray] = None,    # [N, 3]
) -> Dict:
    """
    Compute all 5 paper-standard metrics between one prediction and one GT.

    Returns a dict with keys: chamfer_distance, accuracy_mm, accuracy_median_mm,
    completeness_mm, completeness_median_mm, f_score, outlier_ratio_pred,
    outlier_ratio_gt, normal_consistency, overall_score_mm, hausdorff_max_mm,
    num_points_pred, num_points_gt.
    """
    from scipy.spatial import cKDTree

    M, N = len(pred), len(gt)

    # Build KD-trees (shared for all metrics)
    tree_gt = cKDTree(gt)
    tree_pred = cKDTree(pred)

    # ── Nearest-neighbour queries ──
    dist_p2g, idx_p2g = tree_gt.query(pred, k=1)  # [M] — each pred → nearest GT
    dist_g2p, idx_g2p = tree_pred.query(gt, k=1)   # [N] — each GT → nearest pred

    # ── ① Chamfer Distance ─────────────────────────────────
    cd_term1 = np.mean(dist_p2g ** 2)   # 1/|P| Σ min‖p−g‖²
    cd_term2 = np.mean(dist_g2p ** 2)   # 1/|G| Σ min‖g−p‖²
    chamfer_distance = float(cd_term1 + cd_term2)

    # ── ② Accuracy / Completeness ───────────────────────────
    accuracy_mm        = float(np.mean(dist_p2g)) * 1000.0
    accuracy_median_mm  = float(np.median(dist_p2g)) * 1000.0
    completeness_mm     = float(np.mean(dist_g2p)) * 1000.0
    completeness_median_mm = float(np.median(dist_g2p)) * 1000.0

    # ── ③ F-score ──────────────────────────────────────────
    f_score = {}
    for t in thresholds:
        precision = float(np.mean(dist_p2g < t))
        recall    = float(np.mean(dist_g2p < t))
        f1 = 2.0 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        f_score[f"{t:.2f}m"] = {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        }

    # ── ④ Outlier Ratio ────────────────────────────────────
    outlier_ratio_pred = float(np.mean(dist_p2g > outlier_threshold))
    outlier_ratio_gt   = float(np.mean(dist_g2p > outlier_threshold))

    # ── ⑤ Normal Consistency ───────────────────────────────
    normal_consistency = None
    if pred_normals is not None and gt_normals is not None:
        # For each pred point, compare its normal with the nearest GT point's normal
        gt_normals_matched = gt_normals[idx_p2g]        # [M, 3]
        dot_abs = np.abs(np.sum(pred_normals * gt_normals_matched, axis=1))  # [M]
        dot_abs = np.clip(dot_abs, 0.0, 1.0)
        normal_consistency = float(np.mean(dot_abs))

    # ── Composite ──────────────────────────────────────────
    overall_score_mm = (accuracy_mm + completeness_mm) / 2.0
    hausdorff_max_mm = float(max(np.max(dist_p2g), np.max(dist_g2p))) * 1000.0

    return {
        "num_points_pred": M,
        "num_points_gt": N,
        "chamfer_distance": round(chamfer_distance, 8),
        "accuracy_mm": round(accuracy_mm, 3),
        "accuracy_median_mm": round(accuracy_median_mm, 3),
        "completeness_mm": round(completeness_mm, 3),
        "completeness_median_mm": round(completeness_median_mm, 3),
        "f_score": f_score,
        "outlier_ratio_pred": round(outlier_ratio_pred, 6),
        "outlier_ratio_gt": round(outlier_ratio_gt, 6),
        "normal_consistency": round(normal_consistency, 6) if normal_consistency is not None else None,
        "overall_score_mm": round(overall_score_mm, 3),
        "hausdorff_max_mm": round(hausdorff_max_mm, 3),
    }


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def estimate_normals(points_xyz: np.ndarray, k: int = 10) -> np.ndarray:
    """
    Estimate per-point normals using PCA on k-nearest neighbours.

    No open3d dependency — pure numpy + scipy.

    Args:
        points_xyz: [N, 3] float array.
        k: Number of neighbours for local surface fitting.

    Returns:
        [N, 3] unit normal vectors.
    """
    from scipy.spatial import cKDTree

    N = len(points_xyz)
    if N < k:
        logger.warning(f"Not enough points for normal estimation "
                        f"(have {N}, need k={k}). Returning zeros.")
        return np.zeros((N, 3), dtype=np.float64)

    tree = cKDTree(points_xyz)
    _, idx = tree.query(points_xyz, k=k)  # [N, k]

    # For each point: compute covariance of its k-neighbourhood,
    # eigenvector of smallest eigenvalue = normal.
    normals = np.zeros((N, 3), dtype=np.float64)

    for i in range(N):
        neighbours = points_xyz[idx[i]]           # [k, 3]
        centred = neighbours - neighbours.mean(axis=0)  # [k, 3]
        cov = centred.T @ centred                  # [3, 3]
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        normal = eigenvectors[:, 0]                # smallest eigenvalue
        normals[i] = normal

    # Normalise
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    lengths[lengths < 1e-10] = 1.0
    normals = normals / lengths

    # Orient consistently: flip if normal points away from the centroid
    centroid = points_xyz.mean(axis=0)
    to_centroid = centroid - points_xyz
    dot_sign = np.sum(normals * to_centroid, axis=1)
    normals[dot_sign < 0] *= -1.0

    return normals.astype(np.float32)


def align_point_clouds(
    source: np.ndarray,
    target: np.ndarray,
    max_iterations: int = 50,
    tolerance: float = 1e-6,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Align source to target using ICP (requires open3d).

    Args:
        source: [N, 3] source points.
        target: [M, 3] target points.
        max_iterations: ICP max iterations.
        tolerance: Convergence tolerance.

    Returns:
        (aligned_source [N, 3], transform_4x4)
    """
    try:
        import open3d as o3d
    except ImportError:
        logger.warning("open3d not available for ICP — returning source unchanged")
        return source, np.eye(4, dtype=np.float64)

    src_pcd = o3d.geometry.PointCloud()
    src_pcd.points = o3d.utility.Vector3dVector(source.astype(np.float64))
    tgt_pcd = o3d.geometry.PointCloud()
    tgt_pcd.points = o3d.utility.Vector3dVector(target.astype(np.float64))

    result = o3d.pipelines.registration.registration_icp(
        src_pcd, tgt_pcd,
        max_correspondence_distance=0.5,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        criteria=o3d.pipelines.registration.ICPConvergenceCriteria(
            max_iteration=max_iterations,
            relative_fitness=tolerance,
            relative_rmse=tolerance,
        ),
    )

    aligned = source @ result.transformation[:3, :3].T + result.transformation[:3, 3]
    logger.info(f"ICP: fitness={result.fitness:.4f}, rmse={result.inlier_rmse:.6f}")
    return aligned.astype(np.float64), np.asarray(result.transformation)


def compute_comparison_metrics(
    reference_path: str,
    colmap_path: str,
    mvs_path: str,
    thresholds: Optional[List[float]] = None,
    outlier_threshold: float = 0.10,
    align: bool = False,
    estimate_normal: bool = True,
    normal_k: int = 10,
    max_points: int = 200_000,
) -> Dict:
    """
    Compute paper-standard five-metric suite for 3-way point cloud comparison.

    Compares COLMAP-dense and MVS-network point clouds against a reference
    ground truth, plus an auxiliary COLMAP-vs-MVS comparison.

    Args:
        reference_path: Path to Ground Truth PLY file.
        colmap_path: Path to COLMAP dense PLY file.
        mvs_path: Path to MVS network PLY file.
        thresholds: F-score distance thresholds in metres (default [0.01, 0.02, 0.05]).
        outlier_threshold: Distance (m) above which a point is an outlier.
        align: If True, run ICP to align test clouds to reference.
        estimate_normal: If True, compute Normal Consistency.
        normal_k: Neighbourhood size for PCA normal estimation.
        max_points: Subsample to this many points if exceeded.

    Returns:
        Dict with keys: colmap_vs_gt, mvs_vs_gt, colmap_vs_mvs.
    """
    if thresholds is None:
        thresholds = [0.01, 0.02, 0.05]  # 1cm, 2cm, 5cm — paper standard

    # ── Load ────────────────────────────────────────────────
    logger.info(f"Loading GT:     {reference_path}")
    logger.info(f"Loading COLMAP: {colmap_path}")
    logger.info(f"Loading MVS:    {mvs_path}")

    gt_xyz = _load_xyz(reference_path)
    colmap_xyz = _load_xyz(colmap_path)
    mvs_xyz = _load_xyz(mvs_path)

    logger.info(f"Loaded — GT: {len(gt_xyz)}, COLMAP: {len(colmap_xyz)}, MVS: {len(mvs_xyz)}")

    # ── Optional ICP alignment ──────────────────────────────
    align_transforms = {}
    if align:
        logger.info("Running ICP alignment...")
        colmap_xyz, T_colmap = align_point_clouds(colmap_xyz, gt_xyz)
        align_transforms["colmap_to_gt"] = T_colmap.tolist()
        mvs_xyz, T_mvs = align_point_clouds(mvs_xyz, gt_xyz)
        align_transforms["mvs_to_gt"] = T_mvs.tolist()

    # ── Subsample for efficiency ────────────────────────────
    gt_xyz     = _subsample(gt_xyz, max_points)
    colmap_xyz = _subsample(colmap_xyz, max_points)
    mvs_xyz    = _subsample(mvs_xyz, max_points)

    # ── Normal estimation ──────────────────────────────────
    gt_normals = None
    colmap_normals = None
    mvs_normals = None
    if estimate_normal:
        logger.info(f"Estimating normals (k={normal_k})...")
        try:
            gt_normals     = estimate_normals(gt_xyz, k=normal_k)
            colmap_normals = estimate_normals(colmap_xyz, k=normal_k)
            mvs_normals    = estimate_normals(mvs_xyz, k=normal_k)
        except Exception as e:
            logger.warning(f"Normal estimation failed: {e} — skipping Normal Consistency")

    # ── Compute pairwise metrics ─────────────────────────────
    logger.info("Computing COLMAP vs GT ...")
    colmap_vs_gt = _compute_pairwise_metrics(
        colmap_xyz, gt_xyz,
        thresholds=thresholds,
        outlier_threshold=outlier_threshold,
        pred_normals=colmap_normals,
        gt_normals=gt_normals,
    )

    logger.info("Computing MVS vs GT ...")
    mvs_vs_gt = _compute_pairwise_metrics(
        mvs_xyz, gt_xyz,
        thresholds=thresholds,
        outlier_threshold=outlier_threshold,
        pred_normals=mvs_normals,
        gt_normals=gt_normals,
    )

    logger.info("Computing COLMAP vs MVS ...")
    colmap_vs_mvs = _compute_pairwise_metrics(
        colmap_xyz, mvs_xyz,
        thresholds=thresholds,
        outlier_threshold=outlier_threshold,
        pred_normals=colmap_normals,
        gt_normals=mvs_normals,
    )

    result = {
        "colmap_vs_gt": colmap_vs_gt,
        "mvs_vs_gt": mvs_vs_gt,
        "colmap_vs_mvs": colmap_vs_mvs,
    }

    if align:
        result["align_transforms"] = align_transforms

    # ── Summary log ──────────────────────────────────────────
    logger.info(
        "Comparison complete — COLMAP: Overall=%.2fmm, CD=%.6f | "
        "MVS: Overall=%.2fmm, CD=%.6f",
        colmap_vs_gt["overall_score_mm"],
        colmap_vs_gt["chamfer_distance"],
        mvs_vs_gt["overall_score_mm"],
        mvs_vs_gt["chamfer_distance"],
    )

    return result


def generate_colored_ply(
    points_xyz: np.ndarray,
    distances: np.ndarray,
    output_path: str,
    max_dist: Optional[float] = None,
    original_colors: Optional[np.ndarray] = None,
) -> str:
    """
    Write a PLY file with per-point colors from a green→yellow→red distance heatmap.

    Green  (t=0.0): closest match
    Yellow (t=0.5): moderate error
    Red    (t=1.0): large error

    Args:
        points_xyz: [N, 3] xyz coordinates.
        distances: [N] per-point error distance values.
        output_path: Path to write the PLY.
        max_dist: Distance that maps to red (default: 95th percentile).
        original_colors: Optional [N, 3] original RGB in [0,1] (ignored — distance
                         heatmap always replaces colour).

    Returns:
        output_path
    """
    N = len(points_xyz)

    if max_dist is None or max_dist <= 0:
        max_dist = float(np.percentile(distances, 95))
        if max_dist < 1e-8:
            max_dist = 1e-3  # fallback for near-identical clouds

    # Clamp and normalise to [0, 1]
    t = np.clip(distances / max_dist, 0.0, 1.0)

    # Green → Yellow → Red gradient
    #   t in [0,   0.5]: green (0,1,0) → yellow (1,1,0)
    #   t in [0.5, 1.0]: yellow (1,1,0) → red   (1,0,0)
    rgb = np.zeros((N, 3), dtype=np.float32)
    for i in range(N):
        ti = t[i]
        if ti < 0.5:
            s = ti / 0.5
            rgb[i] = [s, 1.0, 0.0]           # green → yellow
        else:
            s = (ti - 0.5) / 0.5
            rgb[i] = [1.0, 1.0 - s, 0.0]     # yellow → red

    # Build [N, 6] array and reuse DenseFusion's PLY writer
    combined = np.hstack([points_xyz.astype(np.float32), rgb])

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    DenseFusion._write_ply(DenseFusion, output_path, combined)
    logger.info(f"Colored PLY written: {output_path} ({N} points, max_dist={max_dist:.4f})")
    return output_path
