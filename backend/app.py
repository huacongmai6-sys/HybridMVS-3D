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
    SQLALCHEMY_DATABASE_URI,
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

from models import db, Task, init_db
init_db(app)


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Health check ──────────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})


# ── Create task ───────────────────────────────────────────────
@app.route("/api/tasks", methods=["POST"])
def create_task():
    """Upload images and start a reconstruction task."""
    if "images" not in request.files:
        return jsonify({"error": "No images provided"}), 400

    files = request.files.getlist("images")
    quality = request.form.get("quality", "high")
    mode = request.form.get("mode", "colmap")  # "colmap" or "mvs"

    valid_files = [f for f in files if f.filename and _allowed_file(f.filename)]
    if not valid_files:
        return jsonify({"error": "No valid image files (png, jpg, jpeg, tiff, bmp)"}), 400

    # Create task
    task_id = str(uuid.uuid4())
    task = Task(
        id=task_id,
        status="uploading",
        num_images=len(valid_files),
    )
    db.session.add(task)
    db.session.commit()

    # Save uploaded images
    image_dir = os.path.join(UPLOAD_FOLDER, task_id)
    os.makedirs(image_dir, exist_ok=True)

    for f in valid_files:
        filename = f.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]  # sanitize
        f.save(os.path.join(image_dir, filename))

    task.status = "pending"
    db.session.commit()

    # Start reconstruction in background thread
    from tasks import run_reconstruction_async
    run_reconstruction_async(task_id, image_dir, quality, mode)
    logger.info(f"Task {task_id} started in background thread")

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


# ── Run server ───────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Starting HybridMVS API server...")
    logger.info(f"  UPLOAD_FOLDER: {UPLOAD_FOLDER}")
    logger.info(f"  RESULT_FOLDER: {RESULT_FOLDER}")
    logger.info(f"  DATABASE: {SQLALCHEMY_DATABASE_URI}")
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
