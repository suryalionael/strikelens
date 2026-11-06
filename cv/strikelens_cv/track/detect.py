"""Person detection and tracking with Ultralytics YOLO and ByteTrack.

This is the only module that needs the `detect` extra. It is imported lazily, so
the rest of the package and the tests run without it.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from strikelens_cv.track.assign import Detection, FrameInfo
from strikelens_cv.track.config import TrackConfig
from strikelens_cv.track.referee import Pixel, torso_box, torso_dark_share, torso_skin_share

PERSON_CLASS = 0
HUE_BINS = 8
SAT_BINS = 4


def _feature(image: Any, box: Sequence[float]) -> list[float]:
    """Hue and saturation histogram of the band where the shorts are.

    The band is 45-75% down the box and the middle 60% across, to keep out the
    background, the gloves, and the legs. The histogram sums to 1.
    """
    import cv2

    # Clamp to the image: a negative index would wrap around in numpy.
    height, width = image.shape[:2]
    x1, x2 = (min(max(round(v), 0), width) for v in (box[0], box[2]))
    y1, y2 = (min(max(round(v), 0), height) for v in (box[1], box[3]))
    w, h = x2 - x1, y2 - y1
    crop = image[y1 + int(h * 0.45) : y1 + int(h * 0.75), x1 + int(w * 0.2) : x2 - int(w * 0.2)]
    if crop.size == 0:
        return [1.0 / (HUE_BINS * SAT_BINS)] * (HUE_BINS * SAT_BINS)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [HUE_BINS, SAT_BINS], [0, 180, 0, 256]).flatten()
    total = float(hist.sum())
    return [float(v) / total for v in hist] if total > 0 else [0.0] * len(hist)


TORSO_SAMPLE = 16  # the chest is shrunk to 16 x 16 pixels before judging skin


def _torso_pixels(image: Any, box: Sequence[float]) -> list[Pixel]:
    """A small sample of the chest's pixels. Empty when the chest is off the image."""
    import cv2

    height, width = image.shape[:2]
    x1, y1, x2, y2 = torso_box(box)
    x1, x2 = (min(max(round(v), 0), width) for v in (x1, x2))
    y1, y2 = (min(max(round(v), 0), height) for v in (y1, y2))
    crop = image[y1:y2, x1:x2]
    if crop.size == 0:
        return []
    sample = cv2.resize(crop, (TORSO_SAMPLE, TORSO_SAMPLE), interpolation=cv2.INTER_AREA)
    return [(int(px[0]), int(px[1]), int(px[2])) for row in sample.tolist() for px in row]


def _rounded(share: float | None) -> float | None:
    return None if share is None else round(share, 3)


def detect(
    frames_dir: Path,
    frames: Sequence[FrameInfo],
    files: dict[int, str],
    weights: Path,
    config: TrackConfig,
) -> list[Detection]:
    """Track people shot by shot. The tracker starts fresh at every camera cut."""
    try:
        import cv2
        from ultralytics import YOLO
    except ImportError as error:
        raise RuntimeError(
            "Tracking needs the detect extra: cd cv && uv sync --extra ingest --extra detect"
        ) from error

    model = YOLO(str(weights))
    detections: list[Detection] = []
    previous_shot: int | None = None
    for frame in frames:
        if frame["skipped"]:
            continue
        image = cv2.imread(str(frames_dir / files[frame["index"]]))
        if image is None:
            raise FileNotFoundError(f"cannot read frame {files[frame['index']]}")
        result = model.track(
            image,
            persist=frame["shot"] == previous_shot,
            tracker="bytetrack.yaml",
            classes=[PERSON_CLASS],
            conf=config.confidence,
            imgsz=config.image_size,
            verbose=False,
        )[0]
        previous_shot = frame["shot"]
        boxes = result.boxes
        if boxes is None or boxes.id is None:
            continue
        for xyxy, track_id, conf in zip(
            boxes.xyxy.tolist(), boxes.id.int().tolist(), boxes.conf.tolist(), strict=True
        ):
            chest = _torso_pixels(image, xyxy)
            detections.append(
                {
                    "frame": frame["index"],
                    "shot": frame["shot"],
                    "track_id": int(track_id),
                    "box": [round(float(v), 1) for v in xyxy],
                    "confidence": round(float(conf), 3),
                    "feature": [round(v, 4) for v in _feature(image, xyxy)],
                    "torso_skin": _rounded(torso_skin_share(chest, config)),
                    "torso_dark": _rounded(torso_dark_share(chest, config)),
                }
            )
    return detections
