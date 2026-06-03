"""
Video preprocessor: orchestrates frame extraction and selection.

The main entry point — converts a video file into a clean directory
of high-quality images ready for the reconstruction pipeline.
"""

import os
import shutil
import tempfile
import logging

from .extractor import VideoFrameExtractor
from .selector import FrameSelector

logger = logging.getLogger(__name__)


class VideoPreprocessor:
    """
    Convert video to a curated set of reconstruction-ready images.

    Usage:
        preprocessor = VideoPreprocessor(target_frames=30)
        result = preprocessor.process("video.mp4", "./output_frames/")
        # result["image_dir"] → pass directly to Pipeline.run()
    """

    def __init__(
        self,
        target_frames: int = 30,
        blur_threshold: float = 100.0,
        similarity_threshold: float = 0.92,
        min_interval_seconds: float = 0.3,
    ):
        """
        Args:
            target_frames: Target number of output frames after selection.
            blur_threshold: Laplacian variance minimum (default 100).
            similarity_threshold: Max histogram correlation for
                adjacent frames to both be kept (default 0.92).
            min_interval_seconds: Minimum time gap between frames.
        """
        self.target_frames = target_frames
        self.extractor = VideoFrameExtractor(strategy="target_count")
        self.selector = FrameSelector(
            blur_threshold=blur_threshold,
            similarity_threshold=similarity_threshold,
            min_interval_seconds=min_interval_seconds,
        )

    def process(
        self,
        video_path: str,
        output_dir: str,
        progress_callback=None,
    ) -> dict:
        """
        Run the full video-to-images pipeline.

        Args:
            video_path: Path to the video file.
            output_dir: Directory where selected frames will be saved.
            progress_callback: Optional callback(stage: str, percent: int).

        Returns:
            dict with:
              - "image_dir":       Path to selected frames directory.
              - "total_extracted": Number of frames initially extracted.
              - "total_selected":  Number of frames after filtering.
              - "frame_names":     Sorted list of selected frame filenames.
              - "video_info":      Dict with fps, duration_sec, total_frames.
              - "warnings":        List of warning strings.
        """
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        os.makedirs(output_dir, exist_ok=True)
        warnings = []

        # ── Read video metadata ────────────────────────────────────
        video_info = self.extractor.get_video_info(video_path)
        logger.info(
            "Video info: %dx%d, %.1f fps, %.1f sec, %d frames",
            video_info["width"], video_info["height"],
            video_info["fps"], video_info["duration_sec"],
            video_info["total_frames"],
        )

        # Warn on very long videos
        if video_info["duration_sec"] > 120:
            msg = (
                f"Video is {video_info['duration_sec']:.0f}s long. "
                "For best results, keep videos under 2 minutes. "
                "Only a subset of frames will be used."
            )
            warnings.append(msg)
            logger.warning(msg)

        if video_info["width"] < 480 or video_info["height"] < 480:
            msg = (
                f"Video resolution is low ({video_info['width']}x"
                f"{video_info['height']}). Reconstruction quality may "
                "be poor. Use at least 720p video."
            )
            warnings.append(msg)
            logger.warning(msg)

        # ── Stage 1: Extract frames ────────────────────────────────
        if progress_callback:
            progress_callback("extract", 5)

        # Extract 3× target to give the selector room to discard
        extract_count = self.target_frames * 3
        # But don't extract more frames than exist
        max_extract = video_info["total_frames"] // 2
        extract_count = min(extract_count, max_extract)
        extract_count = max(extract_count, self.target_frames)

        raw_dir = tempfile.mkdtemp(prefix="video_raw_")

        try:
            raw_frames = self.extractor.extract(
                video_path,
                output_dir=raw_dir,
                target_frames=extract_count,
                min_interval_frames=3,
            )

            if progress_callback:
                progress_callback("extract", 20)

            if not raw_frames:
                raise RuntimeError("No frames could be extracted from video")

            # ── Stage 2: Select best frames ─────────────────────────
            if progress_callback:
                progress_callback("select", 25)

            selected = self.selector.select(raw_frames)

            if progress_callback:
                progress_callback("select", 50)

            if len(selected) < 5:
                msg = (
                    f"Only {len(selected)} frames survived quality filtering. "
                    "Reconstruction may fail. Try a clearer, slower video "
                    "with more camera motion variety."
                )
                warnings.append(msg)
                logger.warning(msg)

            # ── Stage 3: Copy selected frames to output ─────────────
            if progress_callback:
                progress_callback("finalize", 60)

            frame_names = []
            for i, info in enumerate(selected):
                src = info["path"]
                dst_name = f"frame_{i + 1:04d}.jpg"
                dst_path = os.path.join(output_dir, dst_name)
                shutil.copy2(src, dst_path)
                frame_names.append(dst_name)

            if progress_callback:
                progress_callback("complete", 80)

        finally:
            shutil.rmtree(raw_dir, ignore_errors=True)

        logger.info(
            "Video preprocessing complete: %d raw → %d selected → %s",
            len(raw_frames), len(selected), output_dir,
        )

        return {
            "image_dir": output_dir,
            "total_extracted": len(raw_frames),
            "total_selected": len(selected),
            "frame_names": sorted(frame_names),
            "video_info": video_info,
            "warnings": warnings,
        }
