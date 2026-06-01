"""
Reconstruction task runner.

Supports both Celery (production) and synchronous/threaded (development) modes.
Falls back to threading when Redis/Celery is not available.
"""

import os
import sys
import logging
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import (
    COLMAP_BINARY, MVS_MODEL_TYPE, MVS_IMAGE_WIDTH, MVS_IMAGE_HEIGHT,
    GPU_INDEX, RESULT_FOLDER, MVS_CHECKPOINT,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_reconstruction(task_id: str, image_dir: str, quality: str = "high", mode: str = "colmap"):
    """
    Run the full hybrid reconstruction pipeline synchronously.

    Args:
        task_id: Database task UUID.
        image_dir: Directory containing input images.
        quality: COLMAP feature quality.
        mode: "colmap" (COLMAP PatchMatch, reliable) or "mvs" (CasMVSNet, experimental).
    """
    from models import db, Task, init_db
    from hybridmvs.pipeline import HybridReconstructionPipeline
    from hybridmvs.mvs_network.inference import MVSConfig
    from app import create_app

    app = create_app()
    init_db(app)

    with app.app_context():
        task = db.session.get(Task, task_id)
        if not task:
            return {"error": "Task not found"}

        try:
            task.status = "running"
            task.stage = "sfm_extract_features"
            task.progress = 5
            db.session.commit()

            output_dir = os.path.join(RESULT_FOLDER, task_id)
            workspace_dir = os.path.join(output_dir, "workspace")

            def progress_cb(stage, pct):
                task.stage = stage
                task.progress = min(95, pct)
                db.session.commit()

            mvs_cfg = MVSConfig(
                model_type=MVS_MODEL_TYPE,
                num_views=5,
                img_height=MVS_IMAGE_HEIGHT,
                img_width=MVS_IMAGE_WIDTH,
                device="cuda",
            )

            pipeline = HybridReconstructionPipeline(
                workspace_dir=workspace_dir,
                colmap_binary=COLMAP_BINARY,
                mvs_config=mvs_cfg,
                image_size=(MVS_IMAGE_WIDTH, MVS_IMAGE_HEIGHT),
                gpu_index=GPU_INDEX,
                checkpoint_path=MVS_CHECKPOINT,
                use_colmap_dense=(mode == "colmap"),
            )

            result = pipeline.run(
                image_dir,
                quality=quality,
                progress_callback=progress_cb,
            )

            os.makedirs(output_dir, exist_ok=True)
            paths = pipeline.save_result(result, output_dir)

            task.status = "completed"
            task.progress = 100
            task.stage = "complete"
            task.dense_ply = os.path.relpath(paths.get("ply", ""), RESULT_FOLDER)
            task.dense_obj = os.path.relpath(paths.get("obj", ""), RESULT_FOLDER)
            task.sparse_ply = os.path.relpath(paths.get("sparse", ""), RESULT_FOLDER)
            task.stats_json = os.path.relpath(paths.get("stats", ""), RESULT_FOLDER)

            stats = result.get("stats", {})
            db.session.commit()

            logger.info(f"Task {task_id} completed: {stats}")
            return {"status": "completed", "task_id": task_id, "stats": stats}

        except Exception as e:
            logger.exception(f"Task {task_id} failed")
            task.status = "failed"
            task.error_message = str(e)
            task.stage = "error"
            db.session.commit()
            return {"status": "failed", "task_id": task_id, "error": str(e)}


def run_reconstruction_async(task_id: str, image_dir: str, quality: str = "high", mode: str = "colmap"):
    """Run reconstruction in a background thread."""
    thread = threading.Thread(
        target=run_reconstruction,
        args=(task_id, image_dir, quality, mode),
        daemon=True,
    )
    thread.start()
    return thread
