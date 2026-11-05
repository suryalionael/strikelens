"""Synthetic detections for the track tests. No real footage or real tracks."""

from strikelens_cv.track.assign import Detection

BINS = 32
RED_SHORTS = 3  # histogram bin standing in for the red fighter's shorts colour
BLUE_SHORTS = 20
REFEREE_SHIRT = 30


def feature(bin_: int, purity: float = 0.9) -> list[float]:
    """A histogram with most of its weight in one bin."""
    rest = (1 - purity) / (BINS - 1)
    return [purity if i == bin_ else rest for i in range(BINS)]


def person(
    shot: int,
    track_id: int,
    frames: range,
    x: float,
    colour: int,
    width: float = 100,
    confidence: float = 0.9,
) -> list[Detection]:
    """One tracked person standing at x across the given frames."""
    return [
        {
            "frame": f,
            "shot": shot,
            "track_id": track_id,
            "box": [x, 100.0, x + width, 400.0],
            "confidence": confidence,
            "feature": feature(colour),
        }
        for f in frames
    ]
