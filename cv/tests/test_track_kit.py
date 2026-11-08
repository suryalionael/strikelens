"""Kit colour on synthetic pixels and synthetic fighters. No real footage."""

import pytest

from strikelens_cv.track import TrackConfig, fighter_kit, kit_colour, kit_shares
from strikelens_cv.track.assign import Fighter
from strikelens_cv.track.kit import to_hsv

CONFIG = TrackConfig()

# Synthetic BGR colours (as OpenCV stores them).
RED = {
    "red-singlet": (30, 30, 200),
    "dark-red-singlet": (20, 20, 120),
    # Byon's red singlet as measured: hue 336, between red and magenta (ADR 0006).
    "byon-red-singlet": (112, 74, 168),
}
BLUE = {"blue-singlet": (200, 60, 20), "light-blue-singlet": (230, 140, 60)}
NEITHER = {
    "skin-light": (170, 190, 240),
    "skin-medium": (110, 140, 200),
    "skin-dark": (40, 60, 100),
    "black-shirt": (20, 20, 20),
    # The referee's navy-tinted black shirt under the lights: dark, not blue kit.
    "black-shirt-under-lights": (90, 55, 50),
    "white-shirt": (240, 240, 240),
    "grey-shirt": (128, 128, 128),
    "washed-out-pink": (200, 190, 235),
    "green": (40, 180, 40),
}


def crop(colour: tuple[int, int, int], size: int = 16) -> list[tuple[int, int, int]]:
    return [colour] * (size * size)


def fighter(red: float | None, blue: float | None) -> Fighter:
    return {
        "track_ids": [1],
        "frames": 10,
        "mean_x": 0.0,
        "feature": [],
        "corner": None,
        "kit_red": red,
        "kit_blue": blue,
    }


def test_to_hsv() -> None:
    hue, saturation, value = to_hsv((200, 60, 20))  # BGR, so mostly blue
    assert round(hue) == 227
    assert saturation == pytest.approx(0.9)
    assert value == pytest.approx(200)


@pytest.mark.parametrize("colour", RED.values(), ids=RED.keys())
def test_red_kit(colour: tuple[int, int, int]) -> None:
    assert kit_colour(colour, CONFIG) == "red"


@pytest.mark.parametrize("colour", BLUE.values(), ids=BLUE.keys())
def test_blue_kit(colour: tuple[int, int, int]) -> None:
    assert kit_colour(colour, CONFIG) == "blue"


@pytest.mark.parametrize("colour", NEITHER.values(), ids=NEITHER.keys())
def test_skin_dark_pale_and_other_colours_are_not_kit(colour: tuple[int, int, int]) -> None:
    assert kit_colour(colour, CONFIG) is None


class TestKitShares:
    def test_all_red(self) -> None:
        assert kit_shares(crop(RED["red-singlet"]), CONFIG) == (1.0, 0.0)

    def test_mixed(self) -> None:
        # A blue singlet with arms and gloves across a quarter of the chest.
        pixels = crop(BLUE["blue-singlet"], 8)[:48] + crop(NEITHER["skin-medium"], 4)
        assert kit_shares(pixels, CONFIG) == (0.0, 0.75)

    def test_empty(self) -> None:
        assert kit_shares([], CONFIG) is None


class TestFighterKit:
    def test_clearly_red(self) -> None:
        assert fighter_kit(fighter(0.6, 0.05), CONFIG) == "red"

    def test_clearly_blue(self) -> None:
        assert fighter_kit(fighter(0.0, 0.3), CONFIG) == "blue"  # at the threshold

    def test_unclear(self) -> None:
        assert fighter_kit(fighter(0.4, 0.2), CONFIG) is None
        assert fighter_kit(fighter(0.1, 0.0), CONFIG) is None

    def test_no_measurement(self) -> None:
        assert fighter_kit(fighter(None, None), CONFIG) is None
