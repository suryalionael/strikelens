"""Models that score keypoint windows for "is a strike happening here".

A model takes windows shaped as in windows.py (samples of box-normalised
keypoints, null when missing) and returns, per window, a strike score from 0 to
1 and, if it can tell, a weapon. The trained model from #24 plugs in here.
"""

import math
from collections.abc import Sequence
from itertools import pairwise
from typing import Protocol, TypedDict

from strikelens_cv.strikes.windows import Keypoint


class Prediction(TypedDict):
    strike: float
    weapon: str | None


Samples = Sequence[Sequence[Keypoint] | None]


class StrikeModel(Protocol):
    name: str
    version: str

    def predict(self, windows: Sequence[Samples], sample_ms: float) -> list[Prediction]: ...


# MediaPipe Pose 33 indices of the limbs that strike.
STRIKING = (13, 14, 15, 16, 25, 26, 27, 28)  # elbows, wrists, knees, ankles
MIN_VISIBILITY = 0.5


class MotionBaseline:
    """No training: a window's score is how fast its fastest striking limb moves.

    Speed is in box heights per second between neighbouring samples. The score is a
    logistic curve of the peak speed, 0.5 at `midpoint` box heights a second. It
    cannot tell weapons apart, so the weapon is left for the analyst. These numbers
    are not calibrated on tagged fights; #24 replaces this with a trained model.
    """

    name = "motion-baseline"
    version = "1"

    def __init__(self, midpoint: float = 3.0, width: float = 0.75) -> None:
        self.midpoint = midpoint
        self.width = width

    def peak_speed(self, samples: Samples, sample_ms: float) -> float:
        best = 0.0
        for a, b in pairwise(samples):
            if a is None or b is None:
                continue
            for i in STRIKING:
                if a[i][3] < MIN_VISIBILITY or b[i][3] < MIN_VISIBILITY:
                    continue
                distance = math.hypot(b[i][0] - a[i][0], b[i][1] - a[i][1])
                best = max(best, distance / (sample_ms / 1000))
        return best

    def predict(self, windows: Sequence[Samples], sample_ms: float) -> list[Prediction]:
        out: list[Prediction] = []
        for samples in windows:
            speed = self.peak_speed(samples, sample_ms)
            score = 1 / (1 + math.exp(-(speed - self.midpoint) / self.width))
            out.append({"strike": round(score, 3), "weapon": None})
        return out


MODELS: dict[str, type[MotionBaseline]] = {MotionBaseline.name: MotionBaseline}


def load_model(name: str) -> StrikeModel:
    if name not in MODELS:
        raise ValueError(f"unknown model {name!r}; known: {', '.join(sorted(MODELS))}")
    return MODELS[name]()
