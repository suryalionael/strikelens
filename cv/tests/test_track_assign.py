"""Picking two fighters per shot and keeping them red and blue across cuts."""

import pytest

from strikelens_cv.track import (
    TrackConfig,
    assign_corners,
    build_tracks,
    feature_distance,
    pick_fighters,
    summarise_tracks,
)
from strikelens_cv.track.assign import FrameInfo
from tests.track_cases import BLUE_SHORTS, RED_SHORTS, REFEREE_SHIRT, feature, person

CONFIG = TrackConfig(min_track_frames=3)


def test_feature_distance() -> None:
    assert feature_distance(feature(1), feature(1)) == 0
    assert feature_distance([1.0, 0.0], [0.0, 1.0]) == 1
    with pytest.raises(ValueError):
        feature_distance([1.0], [0.5, 0.5])


def test_summary_of_one_track() -> None:
    [summary] = summarise_tracks(person(0, 7, range(10, 15), x=50, colour=RED_SHORTS))
    assert summary["first_frame"] == 10
    assert summary["last_frame"] == 14
    assert summary["frames"] == 5
    assert summary["mean_area"] == 100 * 300
    assert summary["mean_x"] == 100
    assert feature_distance(summary["feature"], feature(RED_SHORTS)) == pytest.approx(0)


class TestPickFighters:
    def test_two_people(self) -> None:
        tracks = summarise_tracks(
            person(0, 1, range(10), 50, RED_SHORTS) + person(0, 2, range(10), 400, BLUE_SHORTS)
        )
        fighters, dropped = pick_fighters(tracks, CONFIG)
        assert sorted(f["track_ids"] for f in fighters) == [[1], [2]]
        assert dropped == []

    def test_short_tracks_are_dropped(self) -> None:
        passer_by = person(0, 9, range(2), 0, colour=0)
        tracks = summarise_tracks(person(0, 1, range(10), 50, RED_SHORTS) + passer_by)
        fighters, dropped = pick_fighters(tracks, CONFIG)
        assert [f["track_ids"] for f in fighters] == [[1]]
        assert dropped == [9]

    def test_fragment_joins_the_fighter_it_looks_like(self) -> None:
        tracks = summarise_tracks(
            person(0, 1, range(0, 10), 50, RED_SHORTS)
            + person(0, 2, range(0, 20), 400, BLUE_SHORTS)
            + person(0, 3, range(10, 20), 60, RED_SHORTS)  # red again, new ByteTrack ID
        )
        fighters, dropped = pick_fighters(tracks, CONFIG)
        assert sorted(f["track_ids"] for f in fighters) == [[1, 3], [2]]
        assert dropped == []

    def test_third_person_overlapping_both_is_dropped(self) -> None:
        tracks = summarise_tracks(
            person(0, 1, range(20), 50, RED_SHORTS)
            + person(0, 2, range(20), 400, BLUE_SHORTS)
            + person(0, 3, range(5, 15), 250, REFEREE_SHIRT, width=60)
        )
        _, dropped = pick_fighters(tracks, CONFIG)
        assert dropped == [3]

    def test_excluded_tracks_are_dropped(self) -> None:
        tracks = summarise_tracks(person(0, 1, range(10), 50, REFEREE_SHIRT))
        fighters, dropped = pick_fighters(tracks, CONFIG, is_excluded=lambda t: True)
        assert fighters == []
        assert dropped == [1]


def _swapping_sides() -> list:
    """Three shots. The fighters swap sides in shot 1 and come back in shot 2."""
    return (
        person(0, 1, range(0, 10), 50, RED_SHORTS)
        + person(0, 2, range(0, 10), 400, BLUE_SHORTS)
        + person(1, 1, range(10, 20), 400, RED_SHORTS)  # IDs restart after a cut
        + person(1, 2, range(10, 20), 50, BLUE_SHORTS)
        + person(2, 5, range(20, 30), 60, RED_SHORTS)
        + person(2, 6, range(20, 30), 380, BLUE_SHORTS)
    )


class TestAssignCorners:
    def test_left_is_red_seed_is_reported(self) -> None:
        result = assign_corners(summarise_tracks(_swapping_sides()), CONFIG)
        assert result["seeded_by"] == "left_is_red"
        assert result["shots"][0]["red"] == [1]

    def test_identity_follows_colour_not_side(self) -> None:
        result = assign_corners(summarise_tracks(_swapping_sides()), CONFIG)
        assert [(s["red"], s["blue"]) for s in result["shots"]] == [
            ([1], [2]),
            ([1], [2]),  # red is now on the right, still red
            ([5], [6]),
        ]
        assert not any(s["uncertain"] for s in result["shots"])

    def test_a_correction_seeds_and_overrides(self) -> None:
        # The analyst says the right-hand fighter in shot 0 is red.
        result = assign_corners(summarise_tracks(_swapping_sides()), CONFIG, {(0, 2): "red"})
        assert result["seeded_by"] == "corrections"
        assert [(s["red"], s["blue"]) for s in result["shots"]] == [
            ([2], [1]),
            ([2], [1]),
            ([6], [5]),
        ]

    def test_a_none_correction_removes_a_track(self) -> None:
        result = assign_corners(summarise_tracks(_swapping_sides()), CONFIG, {(1, 2): "none"})
        assert result["shots"][1]["blue"] == []
        assert result["shots"][1]["dropped"] == [2]

    def test_one_fighter_in_a_later_shot_goes_to_the_closer_corner(self) -> None:
        detections = _swapping_sides() + person(3, 1, range(30, 40), 200, BLUE_SHORTS)
        result = assign_corners(summarise_tracks(detections), CONFIG)
        assert result["shots"][3]["blue"] == [1]
        assert result["shots"][3]["red"] == []

    def test_one_fighter_in_the_first_shot_is_left_unassigned(self) -> None:
        result = assign_corners(summarise_tracks(person(0, 1, range(10), 50, RED_SHORTS)), CONFIG)
        assert result["shots"][0] == {
            "shot": 0,
            "red": [],
            "blue": [],
            "dropped": [1],
            "uncertain": True,
        }
        assert result["seeded_by"] == "none"

    def test_poor_match_is_uncertain_and_does_not_teach_the_references(self) -> None:
        detections = (
            _swapping_sides()
            + person(3, 1, range(30, 40), 50, 10)  # colours never seen before
            + person(3, 2, range(30, 40), 400, 12)
            + person(4, 1, range(40, 50), 50, RED_SHORTS)
            + person(4, 2, range(40, 50), 400, BLUE_SHORTS)
        )
        result = assign_corners(summarise_tracks(detections), CONFIG)
        assert result["shots"][3]["uncertain"]
        assert (result["shots"][4]["red"], result["shots"][4]["blue"]) == ([1], [2])
        assert not result["shots"][4]["uncertain"]


def test_build_tracks_one_entry_per_frame() -> None:
    detections = (
        person(0, 1, range(0, 3), 50, RED_SHORTS)
        + person(0, 2, range(0, 3), 400, BLUE_SHORTS)
        + person(0, 1, range(2, 3), 55, RED_SHORTS, confidence=0.5)  # weaker duplicate
    )
    frames: list[FrameInfo] = [
        {"index": i, "timestamp_ms": i * 100, "shot": 0, "skipped": i == 1} for i in range(4)
    ]
    assignment = assign_corners(summarise_tracks(detections), TrackConfig(min_track_frames=1))
    out = build_tracks(frames, detections, assignment)
    assert [f["index"] for f in out] == [0, 1, 2, 3]
    assert out[0]["red"] == [50.0, 100.0, 150.0, 400.0]
    assert out[0]["blue"] == [400.0, 100.0, 500.0, 400.0]
    assert out[1] == {"index": 1, "timestamp_ms": 100, "red": None, "blue": None}  # skipped
    assert out[2]["red"] == [50.0, 100.0, 150.0, 400.0]  # the more confident box
    assert out[3]["red"] is None  # nobody seen
