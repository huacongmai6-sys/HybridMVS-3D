"""
Flask REST API for HybridMVS 3D Reconstruction System.

Endpoints:
  POST   /api/tasks              - Upload images and create reconstruction task
  GET    /api/tasks/<id>         - Get task status and results
  GET    /api/tasks/<id>/download/<filetype> - Download results
  DELETE /api/tasks/<id>         - Cancel/delete a task
  GET    /api/health             - Health check
"""

import os
import sys
import uuid
import logging
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from config import (
    SECRET_KEY, DEBUG, UPLOAD_FOLDER, RESULT_FOLDER,
    MAX_CONTENT_LENGTH, ALLOWED_EXTENSIONS,
    SQLALCHEMY_DATABASE_URI, VIDEO_ALLOWED_EXTENSIONS,
    COMPARISON_FOLDER,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["DEBUG"] = DEBUG
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app)
    return app


app = create_app()

from models import db, Task, Comparison, init_db
init_db(app)


def _allowed_image(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _allowed_video(filename: str) -> bool:
    from config import VIDEO_ALLOWED_EXTENSIONS
    return "." in filename and filename.rsplit(".", 1)[1].lower() in VIDEO_ALLOWED_EXTENSIONS


# ── Health check ──────────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})


# ── Create task ───────────────────────────────────────────────
@app.route("/api/tasks", methods=["POST"])
def create_task():
    """Upload images or a video file and start a reconstruction task."""
    quality = request.form.get("quality", "high")
    mode = request.form.get("mode", "colmap")  # "colmap" or "mvs"
    input_type = request.form.get("input_type", "images")  # "images" or "video"

    # Create task
    task_id = str(uuid.uuid4())
    task = Task(
        id=task_id,
        status="uploading",
        num_images=0,
    )
    db.session.add(task)
    db.session.commit()

    image_dir = os.path.join(UPLOAD_FOLDER, task_id)
    os.makedirs(image_dir, exist_ok=True)

    # ── Video input path ────────────────────────────────────────
    if input_type == "video":
        video_file = request.files.get("video")
        if not video_file or not video_file.filename:
            return jsonify({"error": "No video file provided"}), 400
        if not _allowed_video(video_file.filename):
            return jsonify({
                "error": f"Unsupported video format. "
                         f"Allowed: {', '.join(sorted(VIDEO_ALLOWED_EXTENSIONS))}"
            }), 400

        video_filename = video_file.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        video_path = os.path.join(image_dir, video_filename)
        video_file.save(video_path)

        target_frames = int(request.form.get("target_frames", 30))

        task.stage = "video_processing"
        db.session.commit()

        from tasks import run_reconstruction_async
        run_reconstruction_async(
            task_id, image_dir, quality, mode,
            video_path=video_path,
            target_frames=target_frames,
        )
        logger.info(f"Task {task_id} started with video: {video_filename}")

    # ── Image input path ────────────────────────────────────────
    else:
        if "images" not in request.files:
            return jsonify({"error": "No images provided"}), 400

        files = request.files.getlist("images")
        valid_files = [f for f in files if f.filename and _allowed_image(f.filename)]
        if not valid_files:
            return jsonify({"error": "No valid image files (png, jpg, jpeg, tiff, bmp)"}), 400

        task.num_images = len(valid_files)
        db.session.commit()

        for f in valid_files:
            filename = f.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
            f.save(os.path.join(image_dir, filename))

        task.status = "pending"

        # Track uploaded extensions for better UX messages
        uploaded_exts = set()
        for f in files:
            if f.filename:
                ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
                uploaded_exts.add(ext)
        if uploaded_exts - ALLOWED_EXTENSIONS:
            logger.info(
                "Task %s: some files rejected — allowed %s, got %s",
                task_id, ALLOWED_EXTENSIONS, uploaded_exts,
            )

        db.session.commit()

        from tasks import run_reconstruction_async
        run_reconstruction_async(task_id, image_dir, quality, mode)
        logger.info(f"Task {task_id} started with {len(valid_files)} images")

    return jsonify({"task": task.to_dict()}), 202


# ── Run synchronous task (dev fallback) ─────────────────────
@app.route("/api/tasks/<task_id>/run", methods=["POST"])
def run_task_sync(task_id):
    """Run reconstruction synchronously (development only)."""
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    if task.status not in ("pending", "failed"):
        return jsonify({"error": f"Task cannot be started (status: {task.status})"}), 400

    image_dir = os.path.join(UPLOAD_FOLDER, task_id)
    if not os.path.isdir(image_dir):
        return jsonify({"error": "Upload directory not found"}), 400

    from tasks import run_reconstruction
    mode = request.json.get("mode", "colmap") if request.is_json else request.form.get("mode", "colmap")
    result = run_reconstruction(task_id, image_dir, quality="high", mode=mode)
    return jsonify(result)


# ── Get task status ──────────────────────────────────────────
@app.route("/api/tasks/<task_id>")
def get_task(task_id):
    """Get task status and progress."""
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify({"task": task.to_dict()})


# ── List all tasks ───────────────────────────────────────────
@app.route("/api/tasks")
def list_tasks():
    """List all tasks, newest first."""
    tasks = Task.query.order_by(Task.created_at.desc()).limit(50).all()
    return jsonify({"tasks": [t.to_dict() for t in tasks]})


# ── Download results ─────────────────────────────────────────
@app.route("/api/tasks/<task_id>/download/<filetype>")
def download_result(task_id, filetype):
    """Download reconstruction results."""
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    if task.status != "completed":
        return jsonify({"error": "Task not completed"}), 400

    file_map = {
        "ply": task.dense_ply,
        "obj": task.dense_obj,
        "sparse_ply": task.sparse_ply,
        "stats": task.stats_json,
    }

    filename = file_map.get(filetype)
    if not filename:
        return jsonify({"error": f"Unknown file type: {filetype}"}), 400

    filepath = os.path.join(RESULT_FOLDER, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "File not found"}), 404

    directory = os.path.dirname(filepath)
    basename = os.path.basename(filepath)
    return send_from_directory(directory, basename, as_attachment=True)


# ── Depth map previews ───────────────────────────────────────
@app.route("/api/tasks/<task_id>/depth_previews/<filename>")
def serve_depth_preview(task_id, filename):
    """Serve a single depth map preview image."""
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    preview_dir = os.path.join(RESULT_FOLDER, task_id, "depth_previews")
    if not os.path.isdir(preview_dir):
        return jsonify({"error": "No depth previews available"}), 404

    filepath = os.path.join(preview_dir, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "Preview file not found"}), 404

    return send_from_directory(preview_dir, filename)


# ── Delete task ──────────────────────────────────────────────
@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    """Delete a task and its files."""
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    import shutil

    task_dir = os.path.join(RESULT_FOLDER, task_id)
    if os.path.isdir(task_dir):
        shutil.rmtree(task_dir)

    upload_dir = os.path.join(UPLOAD_FOLDER, task_id)
    if os.path.isdir(upload_dir):
        shutil.rmtree(upload_dir)

    db.session.delete(task)
    db.session.commit()

    return jsonify({"status": "deleted"})


# ── Point Cloud Comparison ──────────────────────────────────

def _allowed_ply(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "ply"


@app.route("/api/compare", methods=["POST"])
def create_comparison():
    """
    Upload 3 PLY files and compute paper-standard comparison metrics.

    Multipart form fields:
        gt_file:      (required) Ground Truth PLY
        colmap_file:  (required) COLMAP dense PLY
        mvs_file:     (required) MVS network PLY
        align:        (optional, default "false") ICP alignment
        estimate_normal: (optional, default "true") Normal Consistency
    """
    # ── Validate files ────────────────────────────────────────
    for field, label in [("gt_file", "Ground Truth"), ("colmap_file", "COLMAP"), ("mvs_file", "MVS")]:
        f = request.files.get(field)
        if not f or not f.filename:
            return jsonify({"error": f"Missing file: {label}"}), 400
        if not _allowed_ply(f.filename):
            return jsonify({"error": f"{label} file must be a .ply file"}), 400

    align = request.form.get("align", "false").lower() == "true"
    estimate_normal = request.form.get("estimate_normal", "true").lower() == "true"

    # ── Create comparison record ──────────────────────────────
    comp_id = str(uuid.uuid4())
    comp_dir = os.path.join(COMPARISON_FOLDER, comp_id)
    os.makedirs(comp_dir, exist_ok=True)

    comparison = Comparison(
        id=comp_id,
        status="pending",
        gt_filename=request.files["gt_file"].filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
        colmap_filename=request.files["colmap_file"].filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
        mvs_filename=request.files["mvs_file"].filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
    )
    db.session.add(comparison)
    db.session.commit()

    # ── Save uploaded files ───────────────────────────────────
    gt_path = os.path.join(comp_dir, "gt.ply")
    colmap_path = os.path.join(comp_dir, "colmap.ply")
    mvs_path = os.path.join(comp_dir, "mvs.ply")

    request.files["gt_file"].save(gt_path)
    request.files["colmap_file"].save(colmap_path)
    request.files["mvs_file"].save(mvs_path)

    # ── Compute metrics ───────────────────────────────────────
    try:
        from hybridmvs.evaluation.metrics import (
            compute_comparison_metrics,
            generate_colored_ply,
        )
        import numpy as np
        from hybridmvs.fusion.dense_fusion import DenseFusion

        logger.info(f"Comparison {comp_id}: computing metrics...")
        metrics = compute_comparison_metrics(
            reference_path=gt_path,
            colmap_path=colmap_path,
            mvs_path=mvs_path,
            align=align,
            estimate_normal=estimate_normal,
        )

        # ── Generate colored PLYs ─────────────────────────
        gt_pts = DenseFusion.load_point_cloud(gt_path)
        colmap_pts = DenseFusion.load_point_cloud(colmap_path)
        mvs_pts = DenseFusion.load_point_cloud(mvs_path)

        # Build distance arrays for coloring each cloud
        # For GT: use mean of distances to both COLMAP and MVS (from the per-point data)
        # We recompute quick distances for colouring

        from scipy.spatial import cKDTree

        # GT distances — average of nearest COLMAP and nearest MVS distances
        tree_c = cKDTree(colmap_pts[:, :3])
        tree_m = cKDTree(mvs_pts[:, :3])
        gt_dist_c, _ = tree_c.query(gt_pts[:, :3], k=1)
        gt_dist_m, _ = tree_m.query(gt_pts[:, :3], k=1)
        gt_distances = (gt_dist_c + gt_dist_m) / 2.0

        # COLMAP distances to GT
        tree_gt = cKDTree(gt_pts[:, :3])
        colmap_dist, _ = tree_gt.query(colmap_pts[:, :3], k=1)

        # MVS distances to GT
        mvs_dist, _ = tree_gt.query(mvs_pts[:, :3], k=1)

        gt_colored_path = os.path.join(comp_dir, "gt_colored.ply")
        colmap_colored_path = os.path.join(comp_dir, "colmap_colored.ply")
        mvs_colored_path = os.path.join(comp_dir, "mvs_colored.ply")

        generate_colored_ply(gt_pts[:, :3], gt_distances, gt_colored_path)
        generate_colored_ply(colmap_pts[:, :3], colmap_dist, colmap_colored_path)
        generate_colored_ply(mvs_pts[:, :3], mvs_dist, mvs_colored_path)

        # ── Update record ─────────────────────────────────
        import json
        comparison.status = "completed"
        comparison.metrics_json = json.dumps(metrics)
        comparison.gt_colored_ply = os.path.join(comp_id, "gt_colored.ply")
        comparison.colmap_colored_ply = os.path.join(comp_id, "colmap_colored.ply")
        comparison.mvs_colored_ply = os.path.join(comp_id, "mvs_colored.ply")
        db.session.commit()

        logger.info(f"Comparison {comp_id}: completed")
        return jsonify({"comparison": comparison.to_dict()}), 200

    except Exception as e:
        logger.exception(f"Comparison {comp_id}: failed — {e}")
        comparison.status = "failed"
        comparison.error_message = str(e)
        db.session.commit()
        return jsonify({"error": str(e), "comparison": comparison.to_dict()}), 500


@app.route("/api/compare/<comparison_id>")
def get_comparison(comparison_id):
    """Get comparison status and metric results."""
    comparison = db.session.get(Comparison, comparison_id)
    if not comparison:
        return jsonify({"error": "Comparison not found"}), 404
    return jsonify({"comparison": comparison.to_dict()})


@app.route("/api/compare/<comparison_id>/download/<filetype>")
def download_comparison_result(comparison_id, filetype):
    """Download a colored comparison PLY."""
    comparison = db.session.get(Comparison, comparison_id)
    if not comparison:
        return jsonify({"error": "Comparison not found"}), 404
    if comparison.status != "completed":
        return jsonify({"error": "Comparison not completed"}), 400

    file_map = {
        "gt_colored": comparison.gt_colored_ply,
        "colmap_colored": comparison.colmap_colored_ply,
        "mvs_colored": comparison.mvs_colored_ply,
    }

    filename = file_map.get(filetype)
    if not filename:
        return jsonify({"error": f"Unknown file type: {filetype}. "
                                 f"Use: gt_colored, colmap_colored, mvs_colored"}), 400

    filepath = os.path.join(COMPARISON_FOLDER, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "File not found"}), 404

    directory = os.path.dirname(filepath)
    basename = os.path.basename(filepath)
    return send_from_directory(directory, basename, as_attachment=True)


# ── Run server ───────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Starting HybridMVS API server...")
    logger.info(f"  UPLOAD_FOLDER: {UPLOAD_FOLDER}")
    logger.info(f"  RESULT_FOLDER: {RESULT_FOLDER}")
    logger.info(f"  DATABASE: {SQLALCHEMY_DATABASE_URI}")
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
