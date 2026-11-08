"""Kit colour: in Tryout fights the red corner wears a red singlet, blue a blue one.

The detect stage samples the chest (the same pixels the referee filter uses) and
stores the share of red and of blue kit pixels. `assign_corners` turns a
fighter's shares into a corner (`fighter_kit` in assign.py).

A kit pixel is not skin, not dark, and saturated enough to be a real colour.
Red is a hue of 0-15 or 320-360 degrees, blue 190-250 degrees. Byon's red singlets
measure about 336 degrees, between red and magenta, so the red range reaches down
to 320 (docs/decisions/0006-track-colour-calibration.md). Shirtless fighters
show skin and the referee wears black, so neither has kit and both fall back to
the shorts colour.

Pure Python on plain pixel lists, so it is tested in CI without OpenCV.
"""

import colorsys
from collections.abc import Iterable

from strikelens_cv.track.config import TrackConfig
from strikelens_cv.track.corrections import Corner
from strikelens_cv.track.referee import Pixel, is_skin

RED_HUES = ((0.0, 15.0), (320.0, 360.0))
BLUE_HUES = ((190.0, 250.0),)


def to_hsv(pixel: Pixel) -> tuple[float, float, float]:
    """Hue in degrees (0-360), saturation (0-1), and value (0-255) of a BGR pixel."""
    b, g, r = pixel
    hue, saturation, value = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return hue * 360, saturation, value * 255


def _in(hue: float, ranges: tuple[tuple[float, float], ...]) -> bool:
    return any(low <= hue <= high for low, high in ranges)


def kit_colour(pixel: Pixel, config: TrackConfig) -> Corner | None:
    """The corner colour of a kit pixel. None for skin, dark, pale, or other colours."""
    if max(pixel) <= config.dark_max_value or is_skin(pixel, config):
        return None
    hue, saturation, _ = to_hsv(pixel)
    if saturation < config.kit_min_saturation:
        return None
    if _in(hue, RED_HUES):
        return "red"
    if _in(hue, BLUE_HUES):
        return "blue"
    return None


def kit_shares(pixels: Iterable[Pixel], config: TrackConfig) -> tuple[float, float] | None:
    """Shares of red and of blue kit pixels. None when there are no pixels to judge."""
    total = red = blue = 0
    for pixel in pixels:
        total += 1
        colour = kit_colour(pixel, config)
        red += colour == "red"
        blue += colour == "blue"
    return (red / total, blue / total) if total else None
