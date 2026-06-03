"""
Video preprocessor: convert video input to a set of high-quality frames
suitable for COLMAP SfM and deep learning MVS reconstruction.

Usage:
    from hybridmvs.video_processor import VideoPreprocessor

    preprocessor = VideoPreprocessor(target_frames=30)
    result = preprocessor.process("video.mp4", "./output_frames/")
    # result["image_dir"] → directly passable to Pipeline.run()
"""

from .preprocessor import VideoPreprocessor

__all__ = ["VideoPreprocessor"]
