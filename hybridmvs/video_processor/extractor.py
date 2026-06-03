"""
Frame extractor: reads a video file and outputs individual frames.

Supports "target_count" strategy — evenly samples N frames across the video.
"""

import os
import logging

import cv2

logger = logging.getLogger(__name__)


class VideoFrameExtractor:
    """
    Extract frames from a video file using OpenCV VideoCapture.

    Strategy: "target_count" — extract exactly N frames evenly spaced
    across the full video duration.
    """

    def __init__(self, strategy: str = "target_count"):
        if strategy != "target_count":
            raise ValueError(f"Unsupported strategy: {strategy}")
        self.strategy = strategy

    def extract(
        self,
        video_path: str,
        output_dir: str,
        target_frames: int = 30,
        min_interval_frames: int = 3,
    ) -> list:
        """
        Extract evenly-spaced frames from a video file.

        Args:
            video_path: Path to the video file (mp4/mov/avi/mkv/webm).
            output_dir: Directory to save extracted frame images (JPEG Q=95).
            target_frames: Desired number of output frames.
            min_interval_frames: Minimum frame gap between samples.

        Returns:
            List of dicts:
                {"path": str, "frame_idx": int, "timestamp_sec": float}
        """
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        os.makedirs(output_dir, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / max(fps, 1.0)

        logger.info(
            "Video loaded: %d frames, %.1f fps, %.1f sec duration",
            total_frames, fps, duration,
        )

        # If video has fewer frames than target, take all frames
        actual_target = min(target_frames, total_frames // min_interval_frames)
        actual_target = max(actual_target, 1)

        # Compute sampling interval
        interval = max(min_interval_frames, total_frames // actual_target)

        logger.info(
            "Extracting ~%d frames (interval=%d frames, ~%.1f sec)",
            actual_target, interval, interval / max(fps, 1.0),
        )

        frame_infos = []
        basename = os.path.splitext(os.path.basename(video_path))[0]

        for i in range(actual_target):
            frame_idx = i * interval
            if frame_idx >= total_frames:
                break

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to read frame %d, skipping", frame_idx)
                continue

            filename = f"{basename}_frame_{frame_idx:05d}.jpg"
            filepath = os.path.join(output_dir, filename)

            cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

            timestamp = frame_idx / max(fps, 1.0)
            frame_infos.append({
                "path": filepath,
                "frame_idx": frame_idx,
                "timestamp_sec": round(timestamp, 2),
            })

        cap.release()

        logger.info("Extracted %d frames to %s", len(frame_infos), output_dir)
        return frame_infos

    def get_video_info(self, video_path: str) -> dict:
        """Read video metadata without extracting frames."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        info = {
            "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "duration_sec": 0.0,
        }
        if info["fps"] > 0:
            info["duration_sec"] = info["total_frames"] / info["fps"]
        cap.release()
        return info
