"""Referee filter on synthetic pixel crops and synthetic tracks. No real footage."""

import json
from pathlib import Path

import pytest

from strikelens_cv.cli import main
from strikelens_cv.track import (
    TrackConfig,
    assign_corners,
    is_dark,
    is_referee,
    is_skin,
    load_track_config,
    pick_fighters,
    referee_report,
    summarise_tracks,
    torso_dark_share,
    torso_skin_share,
)
from strikelens_cv.track.assign import Detection
from strikelens_cv.track.referee import referee_score, to_cr_cb, torso_box
from tests.track_cases import BLUE_SHORTS, RED_SHORTS, REFEREE_SHIRT, person

CONFIG = TrackConfig(min_track_frames=3)  # the dark rule, the default
SKIN_RULE = TrackConfig(min_track_frames=3, referee_rule="skin")

# Synthetic BGR colours (as OpenCV stores them).
SKIN_TONES = {
    "light": (170, 190, 240),
    "medium": (110, 140, 200),
    "tan": (80, 120, 180),
    "dark": (40, 60, 100),
    "very-dark": (30, 40, 70),
}
NOT_SKIN = {
    "white-shirt": (240, 240, 240),
    "black-shirt": (20, 20, 20),
    "grey-shirt": (128, 128, 128),
    "blue-canvas": (180, 90, 30),
    "red-shorts": (30, 30, 200),
    "blue-shorts": (200, 60, 20),
}


def crop(colour: tuple[int, int, int], size: int = 16) -> list[tuple[int, int, int]]:
    return [colour] * (size * size)


def with_skin(detections: list[Detection], skin: float | None) -> list[Detection]:
    return [{**d, "torso_skin": skin} for d in detections]


def with_chest(detections: list[Detection], skin: float, dark: float) -> list[Detection]:
    return [{**d, "torso_skin": skin, "torso_dark": dark} for d in detections]


def test_matches_opencv_conversion() -> None:
    # cv2.cvtColor(np.uint8([[[110, 140, 200]]]), cv2.COLOR_BGR2YCrCb) gives Cr 160, Cb 103.
    cr, cb = to_cr_cb((110, 140, 200))
    assert (round(cr), round(cb)) == (160, 103)


@pytest.mark.parametrize("colour", SKIN_TONES.values(), ids=SKIN_TONES.keys())
def test_skin_tones_are_skin(colour: tuple[int, int, int]) -> None:
    assert is_skin(colour, CONFIG)


@pytest.mark.parametrize("colour", NOT_SKIN.values(), ids=NOT_SKIN.keys())
def test_clothes_and_canvas_are_not_skin(colour: tuple[int, int, int]) -> None:
    assert not is_skin(colour, CONFIG)


class TestTorsoSkinShare:
    def test_shirtless_chest_is_skin(self) -> None:
        assert torso_skin_share(crop(SKIN_TONES["dark"]), CONFIG) == 1.0

    def test_shirt_is_not(self) -> None:
        assert torso_skin_share(crop(NOT_SKIN["black-shirt"]), CONFIG) == 0.0

    def test_mixed_crop(self) -> None:
        # A shirt with an open collar: a quarter of the chest shows skin.
        pixels = crop(NOT_SKIN["white-shirt"], 8)[:48] + crop(SKIN_TONES["medium"], 4)
        assert torso_skin_share(pixels, CONFIG) == 0.25

    def test_empty_crop(self) -> None:
        assert torso_skin_share([], CONFIG) is None


DARK = {"black-shirt": (20, 20, 20), "charcoal-shirt": (55, 55, 60)}
NOT_DARK = {
    "red-singlet": (30, 30, 200),
    "blue-singlet": (200, 60, 20),  # pure-ish blue: dark by luma, bright by value
    "white-shirt": (240, 240, 240),
    "grey-shirt": (128, 128, 128),
    "skin-in-shadow": (20, 25, 40),  # dark, but skin
}


@pytest.mark.parametrize("colour", DARK.values(), ids=DARK.keys())
def test_black_clothes_are_dark(colour: tuple[int, int, int]) -> None:
    assert is_dark(colour, CONFIG)


@pytest.mark.parametrize(
    "colour",
    [*NOT_DARK.values(), *SKIN_TONES.values()],
    ids=[*NOT_DARK.keys(), *(f"skin-{k}" for k in SKIN_TONES)],
)
def test_kit_light_clothes_and_skin_are_not_dark(colour: tuple[int, int, int]) -> None:
    assert not is_dark(colour, CONFIG)


class TestTorsoDarkShare:
    def test_black_shirt_is_dark(self) -> None:
        assert torso_dark_share(crop(DARK["black-shirt"]), CONFIG) == 1.0

    def test_singlet_is_not(self) -> None:
        assert torso_dark_share(crop(NOT_DARK["red-singlet"]), CONFIG) == 0.0

    def test_mixed_crop(self) -> None:
        # A black shirt with an open collar: a quarter of the chest shows skin.
        pixels = crop(DARK["black-shirt"], 8)[:48] + crop(SKIN_TONES["very-dark"], 4)
        assert torso_dark_share(pixels, CONFIG) == 0.75

    def test_empty_crop(self) -> None:
        assert torso_dark_share([], CONFIG) is None


def test_torso_box_is_the_chest() -> None:
    assert torso_box([100, 0, 200, 400]) == [125, 80, 175, 180]


def test_referee_score() -> None:
    assert referee_score(0.1) == pytest.approx(0.9)
    assert referee_score(None) is None


class TestIsRefereeSkinRule:
    def _track(self, skin: float | None):  # type: ignore[no-untyped-def]
        [summary] = summarise_tracks(with_skin(person(0, 1, range(5), 0, RED_SHORTS), skin))
        return summary

    def test_below_threshold(self) -> None:
        assert is_referee(self._track(0.05), SKIN_RULE)

    def test_above_threshold(self) -> None:
        assert not is_referee(self._track(0.6), SKIN_RULE)

    def test_filter_off(self) -> None:
        off = TrackConfig(referee_filter=False, referee_rule="skin")
        assert not is_referee(self._track(0.0), off)

    def test_no_measurement_is_kept(self) -> None:
        [summary] = summarise_tracks(person(0, 1, range(5), 0, RED_SHORTS))
        assert summary["torso_skin"] is None
        assert not is_referee(summary, SKIN_RULE)


class TestIsRefereeDarkRule:
    def _track(self, dark: float):  # type: ignore[no-untyped-def]
        [summary] = summarise_tracks(
            with_chest(person(0, 1, range(5), 0, RED_SHORTS), skin=0.0, dark=dark)
        )
        return summary

    def test_dark_rule_is_the_default(self) -> None:
        assert TrackConfig().referee_rule == "dark"

    def test_at_or_above_threshold(self) -> None:
        assert is_referee(self._track(0.5), CONFIG)
        assert is_referee(self._track(0.9), CONFIG)

    def test_below_threshold(self) -> None:
        # No skin on the chest, but not dark either: a fighter in a singlet.
        assert not is_referee(self._track(0.1), CONFIG)

    def test_filter_off(self) -> None:
        assert not is_referee(self._track(1.0), TrackConfig(referee_filter=False))

    def test_no_measurement_is_kept(self) -> None:
        # Detections from before the dark rule have a skin share but no dark share.
        [summary] = summarise_tracks(with_skin(person(0, 1, range(5), 0, RED_SHORTS), 0.0))
        assert summary["torso_dark"] is None
        assert not is_referee(summary, CONFIG)


def _ring_with_big_referee() -> list[Detection]:
    """Shirtless fighters. The referee in black stands close to the camera, so on
    size alone they would win."""
    return (
        with_chest(person(0, 1, range(20), 50, RED_SHORTS), skin=0.7, dark=0.0)
        + with_chest(person(0, 2, range(20), 400, BLUE_SHORTS), skin=0.65, dark=0.05)
        + with_chest(person(0, 3, range(20), 220, REFEREE_SHIRT, width=180), skin=0.02, dark=0.9)
    )


def _tryout_ring() -> list[Detection]:
    """Fighters in red and blue singlets (no skin, not dark), the referee in black."""
    return (
        with_chest(person(0, 1, range(20), 50, RED_SHORTS), skin=0.05, dark=0.0)
        + with_chest(person(0, 2, range(20), 400, BLUE_SHORTS), skin=0.03, dark=0.02)
        + with_chest(person(0, 3, range(20), 220, REFEREE_SHIRT), skin=0.02, dark=0.85)
    )


def test_dark_rule_keeps_fighters_in_singlets() -> None:
    tracks = summarise_tracks(_tryout_ring())
    fighters, dropped = pick_fighters(tracks, CONFIG, is_excluded=lambda t: is_referee(t, CONFIG))
    assert sorted(f["track_ids"] for f in fighters) == [[1], [2]]
    assert dropped == [3]


def test_skin_rule_drops_fighters_in_singlets() -> None:
    # What happened on the first Tryout run: everyone looks like the referee.
    tracks = summarise_tracks(_tryout_ring())
    assert all(is_referee(t, SKIN_RULE) for t in tracks)


def test_the_skin_rule_still_works_on_shirtless_fighters() -> None:
    tracks = summarise_tracks(_ring_with_big_referee())
    fighters, dropped = pick_fighters(
        tracks, SKIN_RULE, is_excluded=lambda t: is_referee(t, SKIN_RULE)
    )
    assert sorted(f["track_ids"] for f in fighters) == [[1], [2]]
    assert dropped == [3]


def test_pick_fighters_drops_the_referee_even_when_biggest() -> None:
    tracks = summarise_tracks(_ring_with_big_referee())
    fighters, dropped = pick_fighters(tracks, CONFIG, is_excluded=lambda t: is_referee(t, CONFIG))
    assert sorted(f["track_ids"] for f in fighters) == [[1], [2]]
    assert dropped == [3]


def test_without_the_filter_the_big_referee_wins_a_slot() -> None:
    tracks = summarise_tracks(_ring_with_big_referee())
    fighters, _ = pick_fighters(tracks, CONFIG)
    assert [3] in [f["track_ids"] for f in fighters]


def test_a_correction_beats_the_filter() -> None:
    # A fighter in a sports top looks like a referee; the analyst pins them.
    tracks = summarise_tracks(_ring_with_big_referee())
    result = assign_corners(
        tracks, CONFIG, {(0, 3): "blue", (0, 2): "none"}, lambda t: is_referee(t, CONFIG)
    )
    assert result["shots"][0]["blue"] == [3]


def test_referee_report() -> None:
    tracks = summarise_tracks(
        with_skin(person(0, 1, range(5), 0, RED_SHORTS), 0.7)
        + with_skin(person(0, 2, range(5), 0, BLUE_SHORTS), 0.1)  # fighter in a top
        + with_skin(person(0, 3, range(5), 0, REFEREE_SHIRT), 0.0)
        + with_skin(person(0, 4, range(5), 0, REFEREE_SHIRT), 0.5)  # missed
        + with_skin(person(0, 5, range(5), 0, REFEREE_SHIRT), 0.0)  # not corrected
    )
    corrections = {(0, 1): "red", (0, 2): "blue", (0, 3): "none", (0, 4): "none"}
    assert referee_report(tracks, corrections, SKIN_RULE) == {  # type: ignore[arg-type]
        "referee_tracks": 2,
        "referee_removed": 0.5,
        "fighter_tracks": 2,
        "fighter_removed": 0.5,
    }


def test_referee_report_with_nothing_to_judge() -> None:
    report = referee_report([], {}, CONFIG)
    assert report["referee_removed"] is None
    assert report["fighter_removed"] is None


class TestConfig:
    def test_ranges_load_from_toml(self, tmp_path: Path) -> None:
        path = tmp_path / "track.toml"
        path.write_text("skin_cr = [130, 170]\nreferee_filter = false\n")
        config = load_track_config(path)
        assert config.skin_cr == (130, 170)
        assert config.referee_filter is False

    def test_dark_rule_loads_from_toml(self, tmp_path: Path) -> None:
        path = tmp_path / "track.toml"
        path.write_text('referee_rule = "skin"\nmin_torso_dark = 0.6\ndark_max_value = 50\n')
        config = load_track_config(path)
        assert (config.referee_rule, config.min_torso_dark, config.dark_max_value) == (
            "skin",
            0.6,
            50,
        )

    @pytest.mark.parametrize(
        "text",
        [
            "skin_cr = [170, 130]\n",
            "skin_cb = [0, 300]\n",
            "skin_cr = [133]\n",
            "min_torso_skin = 2\n",
            'referee_rule = "shirt"\n',
            "min_torso_dark = 1.5\n",
            "dark_max_value = 300\n",
        ],
        ids=[
            "low-above-high",
            "above-255",
            "not-a-pair",
            "share-above-1",
            "unknown-rule",
            "dark-share-above-1",
            "dark-value-above-255",
        ],
    )
    def test_bad_values(self, tmp_path: Path, text: str) -> None:
        path = tmp_path / "track.toml"
        path.write_text(text)
        with pytest.raises(ValueError):
            load_track_config(path)


class TestCli:
    def test_needs_detections(
        self, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        corrections = tmp_path / "c.json"
        corrections.write_text('{"corrections": []}')
        assert main(["referee", "--fight", "fight", "--corrections", str(corrections)]) == 1
        assert "run strikelens-cv track first" in capsys.readouterr().err

    def test_reports_both_shares(
        self, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        out = data_dir / "processed" / "fight"
        out.mkdir(parents=True)
        frames = [
            {"index": i, "timestamp_ms": i * 100, "shot": 0, "skipped": False} for i in range(20)
        ]
        detections = _ring_with_big_referee()
        (out / "detections.json").write_text(
            json.dumps({"frames": frames, "detections": detections})
        )
        corrections = tmp_path / "c.json"
        corrections.write_text(
            json.dumps(
                {
                    "corrections": [
                        {"shot": 0, "track_id": 1, "corner": "red"},
                        {"shot": 0, "track_id": 3, "corner": "none"},
                    ]
                }
            )
        )
        assert main(["referee", "--fight", "fight", "--corrections", str(corrections)]) == 0
        assert capsys.readouterr().out.strip() == (
            "Referee tracks removed: 100% of 1. Fighter tracks wrongly removed: 0% of 1."
        )
