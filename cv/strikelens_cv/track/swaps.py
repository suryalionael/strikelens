"""Count fighter ID swaps by comparing tracks with a corrected version of them."""

from collections.abc import Sequence
from typing import TypedDict

from strikelens_cv.track.assign import Box, TrackFrame

SAME_BOX_IOU = 0.5


class SwapReport(TypedDict):
    swaps: int
    swapped_frames: int
    compared_frames: int


def iou(a: Box | None, b: Box | None) -> float:
    """Intersection over union of two boxes. 0 when either is missing."""
    if a is None or b is None:
        return 0.0
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    inter = w * h
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _is_swapped(auto: TrackFrame, truth: TrackFrame) -> bool:
    red_is_blue = (
        iou(auto["red"], truth["blue"]) >= SAME_BOX_IOU
        and iou(auto["red"], truth["red"]) < SAME_BOX_IOU
    )
    blue_is_red = (
        iou(auto["blue"], truth["red"]) >= SAME_BOX_IOU
        and iou(auto["blue"], truth["blue"]) < SAME_BOX_IOU
    )
    return red_is_blue or blue_is_red


def count_swaps(auto: Sequence[TrackFrame], truth: Sequence[TrackFrame]) -> SwapReport:
    """How often the automatic red and blue are the wrong way round.

    A frame is swapped when the automatic red box is the true blue fighter, or the
    reverse. A swap is a run of swapped frames, so one wrong shot counts once.
    Frames where the truth has no box are not compared.
    """
    truth_by_index = {f["index"]: f for f in truth}
    swaps = swapped_frames = compared = 0
    previous = False
    for frame in sorted(auto, key=lambda f: f["index"]):
        expected = truth_by_index.get(frame["index"])
        if expected is None or (expected["red"] is None and expected["blue"] is None):
            continue
        compared += 1
        now = _is_swapped(frame, expected)
        if now:
            swapped_frames += 1
            if not previous:
                swaps += 1
        previous = now
    return {"swaps": swaps, "swapped_frames": swapped_frames, "compared_frames": compared}
