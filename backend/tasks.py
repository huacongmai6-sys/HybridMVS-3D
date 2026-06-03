"""
Reconstruction task runner.

Supports both Celery (production) and synchronous/threaded (development) modes.
Falls back to threading when Redis/Celery is not available.
"""

import os
import sys
import json
import logging
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import (
    COLMAP_BINARY, MVS_MODEL_TYPE, MVS_IMAGE_WIDTH, MVS_IMAGE_HEIGHT,
    GPU_INDEX, RESULT_FOLDER, MVS_CHECKPOINT,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_reconstruction(
    task_id: str,
    image_dir: str,
    quality: str = "high",
    mode: str = "colmap",
    video_path: str = None,
    target_frames: int = 30,
):
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
            task.progress = 0
            db.session.commit()

            output_dir = os.path.join(RESULT_FOLDER, task_id)
            workspace_dir = os.path.join(output_dir, "workspace")

            # ── Video preprocessing ────────────────────────────────
            image_source_dir = image_dir

            if video_path:
                task.stage = "video_extract"
                task.progress = 1
                db.session.commit()

                from hybridmvs.video_processor import VideoPreprocessor
                from config import (
                    VIDEO_TARGET_FRAMES, VIDEO_BLUR_THRESHOLD,
                    VIDEO_SIMILARITY_THRESHOLD, VIDEO_MIN_INTERVAL_SEC,
                )

                preprocessor = VideoPreprocessor(
                    target_frames=target_frames,
                    blur_threshold=VIDEO_BLUR_THRESHOLD,
                    similarity_threshold=VIDEO_SIMILARITY_THRESHOLD,
                    min_interval_seconds=VIDEO_MIN_INTERVAL_SEC,
                )

                frames_dir = os.path.join(image_dir, "frames")
                os.makedirs(frames_dir, exist_ok=True)

                def video_progress_cb(stage, pct):
                    task.stage = f"video_{stage}"
                    task.progress = max(1, int(pct * 0.08))
                    db.session.commit()

                video_result = preprocessor.process(
                    video_path,
                    frames_dir,
                    progress_callback=video_progress_cb,
                )

                image_source_dir = video_result["image_dir"]
                task.num_images = video_result["total_selected"]
                task.stage = "sfm_extract_features"
                task.progress = 10
                db.session.commit()

                # Log warnings from video preprocessing
                for w in video_result.get("warnings", []):
                    logger.warning("Task %s video: %s", task_id, w)
            else:
                task.stage = "sfm_extract_features"
                task.progress = 5
                db.session.commit()

            def progress_cb(stage, pct):
                # Pipeline progress maps to 10-100% (or 5-100% for image mode)
                base = 10 if video_path else 5
                scale = 0.90 if video_path else 0.95
                task.stage = stage
                task.progress = min(95, base + int(pct * scale))
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
                image_source_dir,
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
            # Depth map previews (JSON)
            previews = paths.get("depth_previews", [])
            task.depth_previews = json.dumps(previews, ensure_ascii=False) if previews else ""

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


def run_reconstruction_async(
    task_id: str,
    image_dir: str,
    quality: str = "high",
    mode: str = "colmap",
    video_path: str = None,
    target_frames: int = 30,
):
    """Run reconstruction in a background thread."""
    thread = threading.Thread(
        target=run_reconstruction,
        args=(task_id, image_dir, quality, mode, video_path, target_frames),
        daemon=True,
    )
    thread.start()
    return thread
