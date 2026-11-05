"""Run pose for one fight: files in, files out. The logic lives in core.py."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from strikelens_cv import __version__
from strikelens_cv.paths import models_dir, processed_dir
from strikelens_cv.pose.backend import PoseBackend
from strikelens_cv.pose.config import PoseConfig
from strikelens_cv.pose.core import CORNERS, Corner, FramePose, frame_pose

MODEL_HELP = (
    "Download pose_landmarker_full.task from "
    "https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker#models and save "
    "it in models/ (gitignored), or set `model` in cv/configs/pose.toml."
)

BackendFactory = Callable[[Path, PoseConfig], PoseBackend]
ImageReader = Callable[[Path], Any]


@dataclass(frozen=True)
class PoseResult:
    out_dir: Path
    frames: dict[Corner, list[FramePose]]


def _read(path: Path, hint: str) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found; {hint}")
    return json.loads(path.read_text())


def model_path(config: PoseConfig) -> Path:
    """The model file in models/. A missing model is an error, never a download."""
    path = models_dir() / config.model
    if not path.is_file():
        raise FileNotFoundError(f"no pose model at {path}. {MODEL_HELP}")
    return path


def _mediapipe(model: Path, config: PoseConfig) -> PoseBackend:
    from strikelens_cv.pose.mediapipe_backend import MediaPipeBackend

    return MediaPipeBackend(model, config)


def _imread(path: Path) -> Any:
    import cv2

    return cv2.imread(str(path))


def _fighter_ids(out_dir: Path) -> dict[Corner, str | None]:
    path = out_dir / "fight.json"
    fight = json.loads(path.read_text()) if path.is_file() else {}
    return {corner: fight.get(f"{corner}_fighter_id") for corner in CORNERS}


def pose(
    fight: str,
    config: PoseConfig,
    backend: BackendFactory | None = None,
    read_image: ImageReader = _imread,
) -> PoseResult:
    """Keypoints for red and blue in every frame. Needs the pose extra.

    Reads frames.json, detections.json (which frames are skipped), and tracks.json
    (the red and blue boxes). Writes keypoints/red.json and keypoints/blue.json.
    Tests pass a fake `backend` and `read_image`, so they need no extras.
    """
    out_dir = processed_dir(fight)
    manifest = _read(out_dir / "frames.json", "run strikelens-cv ingest first")
    labelled = _read(out_dir / "detections.json", "run strikelens-cv track first")["frames"]
    tracks = _read(out_dir / "tracks.json", "run strikelens-cv track first")["frames"]
    model = model_path(config)

    files = {f["index"]: f["file"] for f in manifest["frames"]}
    skipped = {f["index"]: f["skipped"] for f in labelled}
    estimator = (backend or _mediapipe)(model, config)
    results: dict[Corner, list[FramePose]] = {corner: [] for corner in CORNERS}
    try:
        for frame in tracks:
            index = frame["index"]
            is_skipped = skipped.get(index, False)
            image = None
            if not is_skipped and any(frame[c] for c in CORNERS):
                image = read_image(out_dir / "frames" / files[index])
                if image is None:
                    raise FileNotFoundError(f"cannot read frame {files[index]}")
            for corner in CORNERS:
                box = frame[corner]
                keypoints = None
                if image is not None and box is not None:
                    keypoints = estimator.estimate(image, box)
                results[corner].append(
                    frame_pose(index, frame["timestamp_ms"], is_skipped, box, keypoints)
                )
    finally:
        estimator.close()

    keypoints_dir = out_dir / "keypoints"
    keypoints_dir.mkdir(exist_ok=True)
    fighter_ids = _fighter_ids(out_dir)
    for corner in CORNERS:
        data = {
            "strikelens_cv": __version__,
            "format": estimator.format,
            "landmarks": list(estimator.landmark_names),
            "keypoint_fields": ["x", "y", "z", "visibility"],
            "corner": corner,
            "fighter_id": fighter_ids[corner],
            "config": config.as_dict(),
            "frames": results[corner],
        }
        (keypoints_dir / f"{corner}.json").write_text(json.dumps(data) + "\n")
    return PoseResult(out_dir=keypoints_dir, frames=results)
