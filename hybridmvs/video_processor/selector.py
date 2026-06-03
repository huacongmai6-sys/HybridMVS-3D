"""
Frame selector: filters extracted frames by quality and redundancy.

Three-stage pipeline:
  1. Blur detection — discard motion-blurred / out-of-focus frames
  2. Redundancy removal — discard near-duplicate adjacent frames
  3. Minimum interval enforcement — ensure temporal spacing
"""

import os
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FrameSelector:
    """
    Filter frame candidates to keep only high-quality, non-redundant
    frames suitable for SfM reconstruction.
    """

    def __init__(
        self,
        blur_threshold: float = 100.0,
        similarity_threshold: float = 0.92,
        min_interval_seconds: float = 0.3,
    ):
        """
        Args:
            blur_threshold: Laplacian variance threshold.
                Frames with variance below this are discarded.
            similarity_threshold: Histogram correlation threshold.
                Adjacent frames above this are considered redundant.
            min_interval_seconds: Minimum time gap between selected frames.
        """
        self.blur_threshold = blur_threshold
        self.similarity_threshold = similarity_threshold
        self.min_interval_seconds = min_interval_seconds

    def select(self, frame_infos: list) -> list:
        """
        Filter frames through quality and redundancy checks.

        Args:
            frame_infos: List from VideoFrameExtractor.extract().

        Returns:
            Filtered list in the same format.
        """
        if not frame_infos:
            logger.warning("No frames to select from")
            return []

        logger.info(
            "Selecting from %d frames (blur<%g, sim<%g, gap>%gs)",
            len(frame_infos),
            self.blur_threshold,
            self.similarity_threshold,
            self.min_interval_seconds,
        )

        # ── Stage 1: Blur detection ──────────────────────────────
        sharp_frames = []
        for info in frame_infos:
            img = cv2.imread(info["path"])
            if img is None:
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()

            if lap_var >= self.blur_threshold:
                info["_lap_var"] = lap_var
                sharp_frames.append(info)
            else:
                logger.debug(
                    "Discarding blurry frame %d (laplacian=%.1f)",
                    info["frame_idx"], lap_var,
                )

        blur_discarded = len(frame_infos) - len(sharp_frames)
        logger.info(
            "Stage 1 (blur): %d/%d kept (%d discarded)",
            len(sharp_frames), len(frame_infos), blur_discarded,
        )

        if not sharp_frames:
            logger.warning("All frames discarded by blur detection — "
                           "trying relaxed threshold")
            return self._relaxed_select(frame_infos)

        # ── Stage 2: Redundancy removal ───────────────────────────
        unique_frames = [sharp_frames[0]]

        for i in range(1, len(sharp_frames)):
            prev_img = cv2.imread(sharp_frames[i - 1]["path"])
            curr_img = cv2.imread(sharp_frames[i]["path"])
            if prev_img is None or curr_img is None:
                continue

            # 3D color histogram comparison
            hist_prev = cv2.calcHist(
                [prev_img], [0, 1, 2], None, [64, 64, 64],
                [0, 256, 0, 256, 0, 256],
            )
            hist_curr = cv2.calcHist(
                [curr_img], [0, 1, 2], None, [64, 64, 64],
                [0, 256, 0, 256, 0, 256],
            )
            cv2.normalize(hist_prev, hist_prev)
            cv2.normalize(hist_curr, hist_curr)

            similarity = cv2.compareHist(
                hist_prev, hist_curr, cv2.HISTCMP_CORREL,
            )

            if similarity < self.similarity_threshold:
                unique_frames.append(sharp_frames[i])
            else:
                logger.debug(
                    "Discarding redundant frame %d (sim=%.3f)",
                    sharp_frames[i]["frame_idx"], similarity,
                )

        redun_discarded = len(sharp_frames) - len(unique_frames)
        logger.info(
            "Stage 2 (redundancy): %d/%d kept (%d discarded)",
            len(unique_frames), len(sharp_frames), redun_discarded,
        )

        # ── Stage 3: Minimum interval enforcement ─────────────────
        spaced_frames = [unique_frames[0]]
        last_ts = unique_frames[0]["timestamp_sec"]

        for i in range(1, len(unique_frames)):
            dt = unique_frames[i]["timestamp_sec"] - last_ts
            if dt >= self.min_interval_seconds:
                spaced_frames.append(unique_frames[i])
                last_ts = unique_frames[i]["timestamp_sec"]

        interval_discarded = len(unique_frames) - len(spaced_frames)
        logger.info(
            "Stage 3 (interval): %d/%d kept (%d discarded)",
            len(spaced_frames), len(unique_frames), interval_discarded,
        )

        # Clean up internal keys
        for f in spaced_frames:
            f.pop("_lap_var", None)

        return spaced_frames

    def _relaxed_select(self, frame_infos: list) -> list:
        """Fallback: relax blur threshold and retry."""
        relaxed = FrameSelector(
            blur_threshold=self.blur_threshold * 0.5,
            similarity_threshold=min(self.similarity_threshold + 0.05, 0.99),
            min_interval_seconds=self.min_interval_seconds,
        )
        return relaxed.select(frame_infos)
