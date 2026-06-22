"""SQLAlchemy database models."""
import uuid
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Comparison(db.Model):
    """Point cloud comparison result record (3-way: GT vs COLMAP vs MVS)."""
    __tablename__ = "comparisons"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = db.Column(db.String(20), default="pending")  # pending, completed, failed
    gt_filename = db.Column(db.String(500), default="")       # Ground Truth filename
    colmap_filename = db.Column(db.String(500), default="")   # COLMAP dense filename
    mvs_filename = db.Column(db.String(500), default="")      # MVS network filename
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Full 5-metric JSON (chamfer, accuracy/completeness, f-score, outlier, normal)
    metrics_json = db.Column(db.Text, default="")

    # Colored PLY paths (relative to COMPARISON_FOLDER)
    gt_colored_ply = db.Column(db.String(500), default="")
    colmap_colored_ply = db.Column(db.String(500), default="")
    mvs_colored_ply = db.Column(db.String(500), default="")

    error_message = db.Column(db.Text, default="")

    def to_dict(self):
        import json
        try:
            metrics = json.loads(self.metrics_json) if self.metrics_json else None
        except (json.JSONDecodeError, TypeError):
            metrics = None
        return {
            "id": self.id,
            "status": self.status,
            "gt_filename": self.gt_filename,
            "colmap_filename": self.colmap_filename,
            "mvs_filename": self.mvs_filename,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metrics": metrics,
            "gt_colored_ply": self.gt_colored_ply,
            "colmap_colored_ply": self.colmap_colored_ply,
            "mvs_colored_ply": self.mvs_colored_ply,
            "error_message": self.error_message,
        }


class Task(db.Model):
    """Reconstruction task record."""
    __tablename__ = "tasks"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = db.Column(db.String(20), default="pending")  # pending, running, completed, failed
    progress = db.Column(db.Integer, default=0)            # 0-100
    stage = db.Column(db.String(50), default="")           # current stage name
    num_images = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    error_message = db.Column(db.Text, default="")

    # Output paths (relative to result folder)
    dense_ply = db.Column(db.String(500), default="")
    dense_obj = db.Column(db.String(500), default="")
    sparse_ply = db.Column(db.String(500), default="")
    stats_json = db.Column(db.String(500), default="")
    depth_previews = db.Column(db.Text, default="")  # JSON array of preview metadata

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "progress": self.progress,
            "stage": self.stage,
            "num_images": self.num_images,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "error_message": self.error_message,
            "dense_ply": self.dense_ply,
            "dense_obj": self.dense_obj,
            "sparse_ply": self.sparse_ply,
            "stats_json": self.stats_json,
            "depth_previews": self._parse_depth_previews(),
        }

    def _parse_depth_previews(self):
        """Parse depth_previews JSON string, or return empty list."""
        import json
        try:
            return json.loads(self.depth_previews) if self.depth_previews else []
        except (json.JSONDecodeError, TypeError):
            return []


def init_db(app):
    """Initialize the database."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
