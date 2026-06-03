"""SQLAlchemy database models."""
import uuid
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


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
