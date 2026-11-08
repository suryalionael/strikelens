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
            "by_kit": False,
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


RED_KIT = (0.8, 0.0)
BLUE_KIT = (0.0, 0.8)


def _shorts_fooled() -> list:
    """Tryout fighters in singlets. In shot 1 the shorts band picks up the wrong
    colour (the ropes, the other fighter), so by shorts alone they would swap."""
    return (
        person(0, 1, range(0, 10), 50, RED_SHORTS, kit=RED_KIT)
        + person(0, 2, range(0, 10), 400, BLUE_SHORTS, kit=BLUE_KIT)
        + person(1, 1, range(10, 20), 400, BLUE_SHORTS, kit=RED_KIT)
        + person(1, 2, range(10, 20), 50, RED_SHORTS, kit=BLUE_KIT)
    )


class TestKitColour:
    def test_kit_beats_left_is_red(self) -> None:
        # Red corner stands on the right in the first shot.
        detections = person(0, 1, range(10), 50, BLUE_SHORTS, kit=BLUE_KIT) + person(
            0, 2, range(10), 400, RED_SHORTS, kit=RED_KIT
        )
        result = assign_corners(summarise_tracks(detections), CONFIG)
        assert result["seeded_by"] == "kit"
        assert (result["shots"][0]["red"], result["shots"][0]["blue"]) == ([2], [1])
        assert result["shots"][0]["by_kit"]

    def test_kit_beats_the_shorts_in_every_shot(self) -> None:
        result = assign_corners(summarise_tracks(_shorts_fooled()), CONFIG)
        assert [(s["red"], s["blue"]) for s in result["shots"]] == [([1], [2]), ([1], [2])]
        assert all(s["by_kit"] for s in result["shots"])

    def test_with_kit_off_the_shorts_decide(self) -> None:
        off = TrackConfig(min_track_frames=3, kit_corner=False)
        result = assign_corners(summarise_tracks(_shorts_fooled()), off)
        assert result["seeded_by"] == "left_is_red"
        assert result["shots"][1]["red"] == [2]  # the swap the kit prevents
        assert not any(s["by_kit"] for s in result["shots"])

    def test_one_fighter_in_kit_in_the_first_shot_is_assigned(self) -> None:
        detections = person(0, 1, range(10), 50, BLUE_SHORTS, kit=BLUE_KIT)
        result = assign_corners(summarise_tracks(detections), CONFIG)
        assert result["shots"][0]["blue"] == [1]
        assert not result["shots"][0]["uncertain"]

    def test_two_fighters_in_the_same_kit_fall_back_to_the_shorts(self) -> None:
        detections = _swapping_sides() + (
            person(3, 1, range(30, 40), 400, RED_SHORTS, kit=RED_KIT)
            + person(3, 2, range(30, 40), 50, BLUE_SHORTS, kit=RED_KIT)
        )
        result = assign_corners(summarise_tracks(detections), CONFIG)
        assert (result["shots"][3]["red"], result["shots"][3]["blue"]) == ([1], [2])
        assert not result["shots"][3]["by_kit"]

    def test_a_correction_beats_the_kit(self) -> None:
        # The analyst pins track 2 as red; track 1's kit also says red, so the kit
        # is not trusted in this shot.
        detections = person(0, 1, range(10), 50, RED_SHORTS, kit=RED_KIT) + person(
            0, 2, range(10), 400, BLUE_SHORTS, kit=BLUE_KIT
        )
        result = assign_corners(summarise_tracks(detections), CONFIG, {(0, 2): "red"})
        assert result["seeded_by"] == "corrections"
        assert (result["shots"][0]["red"], result["shots"][0]["blue"]) == ([2], [1])
        assert not result["shots"][0]["by_kit"]

    def test_shirtless_fighters_are_not_decided_by_kit(self) -> None:
        result = assign_corners(summarise_tracks(_swapping_sides()), CONFIG)
        assert result["seeded_by"] == "left_is_red"
        assert not any(s["by_kit"] for s in result["shots"])


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


class TestLongShots:
    """Round 1 of a Tryout broke into 80 to 114 tracks per shot. These are the three
    errors that caused, rebuilt with synthetic tracks."""

    def test_a_kit_track_overlapping_its_own_corner_is_kept(self) -> None:
        # The blue fighter's long track (2) overlaps a short blue track (3), for
        # example a box on the head only. Before, 2 was dropped as a third person.
        detections = (
            person(0, 1, range(0, 20), 50, RED_SHORTS, kit=RED_KIT)
            + person(0, 2, range(0, 20), 400, BLUE_SHORTS, kit=BLUE_KIT)
            + person(0, 3, range(5, 15), 410, BLUE_SHORTS, kit=BLUE_KIT)
        )
        shot = assign_corners(summarise_tracks(detections), CONFIG)["shots"][0]
        assert (shot["red"], shot["blue"], shot["dropped"]) == ([1], [2, 3], [])
        assert shot["by_kit"]

    def test_a_fragment_follows_its_kit_not_its_shorts(self) -> None:
        # Track 3 continues the red fighter, but its shorts band picked up blue.
        # Before, it could join the blue fighter and swap the corners.
        detections = (
            person(0, 1, range(0, 10), 50, RED_SHORTS, kit=RED_KIT)
            + person(0, 2, range(0, 10), 400, BLUE_SHORTS, kit=BLUE_KIT)
            + person(0, 3, range(10, 20), 60, BLUE_SHORTS, kit=RED_KIT)
        )
        shot = assign_corners(summarise_tracks(detections), CONFIG)["shots"][0]
        assert (shot["red"], shot["blue"]) == ([1, 3], [2])

    def test_a_small_person_in_the_crowd_is_not_a_fighter(self) -> None:
        # Track 5 is a spectator behind the ropes, seen after track 1 ends. Before,
        # it joined track 1 as a fragment because it did not overlap it in time.
        detections = (
            person(0, 1, range(0, 10), 50, RED_SHORTS)
            + person(0, 2, range(0, 20), 400, BLUE_SHORTS)
            + person(0, 5, range(12, 20), 700, RED_SHORTS, width=25)
        )
        fighters, dropped = pick_fighters(summarise_tracks(detections), CONFIG)
        assert sorted(f["track_ids"] for f in fighters) == [[1], [2]]
        assert dropped == [5]

    def test_the_size_check_can_be_turned_off(self) -> None:
        detections = person(0, 1, range(0, 10), 50, RED_SHORTS) + person(
            0, 5, range(12, 20), 700, RED_SHORTS, width=25
        )
        config = TrackConfig(min_track_frames=3, min_fighter_area=0)
        fighters, dropped = pick_fighters(summarise_tracks(detections), config)
        assert [f["track_ids"] for f in fighters] == [[1, 5]]
        assert dropped == []

    def test_the_size_check_counts_the_referee(self) -> None:
        # The referee (track 9) is the biggest box and is dropped by the filter.
        # Measured against the fighters only, spectator 5 would pass as a fighter.
        detections = (
            person(0, 1, range(0, 10), 50, RED_SHORTS, width=60)
            + person(0, 2, range(0, 20), 400, BLUE_SHORTS, width=60)
            + person(0, 9, range(0, 20), 250, REFEREE_SHIRT, width=120)
            + person(0, 5, range(12, 20), 700, RED_SHORTS, width=30)
        )
        fighters, dropped = pick_fighters(
            summarise_tracks(detections), CONFIG, is_excluded=lambda t: t["track_id"] == 9
        )
        assert sorted(f["track_ids"] for f in fighters) == [[1], [2]]
        assert dropped == [5, 9]
