"""MediaPipe Pose Landmarker on one fighter crop at a time.

This is the only module that needs the `pose` extra. It is imported lazily, so
the rest of the package and the tests run without it.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from strikelens_cv.pose.config import PoseConfig
from strikelens_cv.pose.core import (
    MEDIAPIPE_LANDMARKS,
    MEDIAPIPE_POSE_33,
    Keypoint,
    crop_box,
    to_image,
)


class MediaPipeBackend:
    format = MEDIAPIPE_POSE_33
    landmark_names = MEDIAPIPE_LANDMARKS

    def __init__(self, model: Path, config: PoseConfig) -> None:
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions, vision
        except ImportError as error:
            raise RuntimeError(
                "Pose needs the pose extra: cd cv && uv sync --extra ingest --extra pose"
            ) from error
        self._mp = mp
        self._config = config
        options = vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model)),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=config.min_pose_confidence,
            min_pose_presence_confidence=config.min_pose_confidence,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(options)

    def estimate(self, image: Any, box: Sequence[float]) -> list[Keypoint] | None:
        import cv2
        import numpy as np

        height, width = image.shape[:2]
        crop = crop_box(box, width, height, self._config.box_margin)
        if crop is None:
            return None
        x1, y1, x2, y2 = (int(v) for v in crop)
        rgb = np.ascontiguousarray(cv2.cvtColor(image[y1:y2, x1:x2], cv2.COLOR_BGR2RGB))
        result = self._landmarker.detect(
            self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        )
        if not result.pose_landmarks:
            return None
        landmarks = [
            (p.x or 0.0, p.y or 0.0, p.z or 0.0, p.visibility or 0.0)
            for p in result.pose_landmarks[0]
        ]
        return to_image(landmarks, crop)

    def close(self) -> None:
        self._landmarker.close()
