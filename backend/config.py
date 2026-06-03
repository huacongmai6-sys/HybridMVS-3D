"""Flask backend configuration."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

# Flask
SECRET_KEY = os.environ.get("SECRET_KEY", "hybridmvs-secret-key-change-in-production")
DEBUG = os.environ.get("DEBUG", "true").lower() == "true"

# File storage
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
RESULT_FOLDER = os.path.join(BASE_DIR, "results")
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB upload limit
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "tiff", "tif", "bmp"}

# Celery / Redis
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/1")

# Database
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'hybridmvs.db')}",
)

# COLMAP
COLMAP_BINARY = os.environ.get(
    "COLMAP_BINARY",
    os.path.join(os.path.expanduser("~"), "colmap", "bin", "colmap.exe"),
)

# MVS Model
MVS_MODEL_TYPE = os.environ.get("MVS_MODEL_TYPE", "patchmatchnet")
MVS_IMAGE_WIDTH = int(os.environ.get("MVS_IMAGE_WIDTH", "640"))
MVS_IMAGE_HEIGHT = int(os.environ.get("MVS_IMAGE_HEIGHT", "512"))
GPU_INDEX = int(os.environ.get("GPU_INDEX", "0"))
MVS_CHECKPOINT = os.environ.get(
    "MVS_CHECKPOINT",
    os.path.join(PROJECT_DIR, "checkpoints", "model_000007.ckpt"),
)

# Video processing
VIDEO_ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}
VIDEO_MAX_DURATION_SEC = 120
VIDEO_TARGET_FRAMES = 30
VIDEO_BLUR_THRESHOLD = 100.0
VIDEO_SIMILARITY_THRESHOLD = 0.92
VIDEO_MIN_INTERVAL_SEC = 0.3
