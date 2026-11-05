"""Referee filter: kickboxers fight shirtless, the referee wears a shirt.

The signal is how much of a person's chest is skin. Skin is found with the usual
YCrCb rule: convert each pixel and check its Cr and Cb against a range. Brightness
(Y) is ignored, which is what makes one range work for light and dark skin.

Pure Python on plain pixel lists, so it is tested in CI without OpenCV. The detect
stage samples a small grid of chest pixels per box and calls these functions.
"""

from collections.abc import Iterable, Sequence
from typing import TypedDict

from strikelens_cv.track.assign import Box, TrackSummary
from strikelens_cv.track.config import TrackConfig
from strikelens_cv.track.corrections import Corrections

Pixel = tuple[int, int, int]  # B, G, R, as OpenCV reads images


class RefereeReport(TypedDict):
    referee_tracks: int
    referee_removed: float | None
    fighter_tracks: int
    fighter_removed: float | None


def to_cr_cb(pixel: Pixel) -> tuple[float, float]:
    """Cr and Cb of a BGR pixel (ITU-R BT.601, full range, as OpenCV computes them)."""
    b, g, r = pixel
    y = 0.299 * r + 0.587 * g + 0.114 * b
    return (r - y) * 0.713 + 128, (b - y) * 0.564 + 128


def is_skin(pixel: Pixel, config: TrackConfig) -> bool:
    cr, cb = to_cr_cb(pixel)
    return (
        config.skin_cr[0] <= cr <= config.skin_cr[1]
        and config.skin_cb[0] <= cb <= config.skin_cb[1]
    )


def torso_skin_share(pixels: Iterable[Pixel], config: TrackConfig) -> float | None:
    """Share of skin pixels, from 0 to 1. None when there are no pixels to judge."""
    total = skin = 0
    for pixel in pixels:
        total += 1
        skin += is_skin(pixel, config)
    return skin / total if total else None


def torso_box(box: Sequence[float]) -> Box:
    """The chest: 20-45% down the person box and the middle half across.

    High enough to miss the shorts and narrow enough to miss arms and gloves.
    """
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    return [x1 + w * 0.25, y1 + h * 0.20, x2 - w * 0.25, y1 + h * 0.45]


def referee_score(skin_share: float | None) -> float | None:
    """How referee-like a chest looks, from 0 (all skin) to 1 (no skin)."""
    return None if skin_share is None else 1 - skin_share


def is_referee(track: TrackSummary, config: TrackConfig) -> bool:
    """True when the filter is on and the track's chest is mostly not skin.

    A track without a measurement (detections from before #20) is kept.
    """
    skin = track["torso_skin"]
    return config.referee_filter and skin is not None and skin < config.min_torso_skin


def referee_report(
    tracks: Sequence[TrackSummary], corrections: Corrections, config: TrackConfig
) -> RefereeReport:
    """How well the filter does, with the corrections as the truth.

    A track corrected to "none" counts as the referee; one corrected to red or blue
    counts as a fighter. Tracks without a correction are not judged.
    """
    referee = removed_referee = fighter = removed_fighter = 0
    for t in tracks:
        truth = corrections.get((t["shot"], t["track_id"]))
        if truth is None:
            continue
        removed = is_referee(t, config)
        if truth == "none":
            referee += 1
            removed_referee += removed
        else:
            fighter += 1
            removed_fighter += removed
    return {
        "referee_tracks": referee,
        "referee_removed": removed_referee / referee if referee else None,
        "fighter_tracks": fighter,
        "fighter_removed": removed_fighter / fighter if fighter else None,
    }
