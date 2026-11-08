"""Splitting tracks where ByteTrack passed the ID to another person. Synthetic only."""

import json
from pathlib import Path

from strikelens_cv.track import TrackConfig, assign
from strikelens_cv.track.assign import Detection, assign_corners, summarise_tracks
from strikelens_cv.track.split import cut_points, is_split, split_switches
from tests.track_cases import BLUE_SHORTS, RED_SHORTS, person

CONFIG = TrackConfig(min_track_frames=3)
RED_KIT = (0.8, 0.0)
BLUE_KIT = (0.0, 0.8)


def switching(
    shot: int, track_id: int, first: list[Detection], second: list[Detection]
) -> list[Detection]:
    """One ByteTrack ID on two people: `first`, then `second`."""
    return [{**d, "track_id": track_id} for d in first + second]


def ids(detections: list[Detection]) -> dict[int, list[int]]:
    """Frames per track ID."""
    out: dict[int, list[int]] = {}
    for d in detections:
        out.setdefault(d["track_id"], []).append(d["frame"])
    return out


def test_a_track_that_changes_kit_is_cut_where_it_changes() -> None:
    track = switching(
        0,
        1,
        person(0, 1, range(0, 10), 400, RED_SHORTS, kit=RED_KIT),
        person(0, 1, range(10, 20), 400, BLUE_SHORTS, kit=BLUE_KIT),
    )
    assert cut_points(track, CONFIG) == [10]
    pieces = ids(split_switches(track, CONFIG))
    assert pieces == {1: list(range(10)), 2: list(range(10, 20))}


def test_a_track_that_turns_dark_is_cut() -> None:
    # A fighter's ID passes to the referee in black.
    fighter = person(0, 1, range(0, 10), 400, RED_SHORTS)
    referee = person(0, 1, range(10, 20), 400, RED_SHORTS)
    for d in fighter:
        d["torso_dark"] = 0.05
    for d in referee:
        d["torso_dark"] = 0.8
    assert cut_points(fighter + referee, CONFIG) == [10]


def test_a_box_that_jumps_sideways_is_cut() -> None:
    track = person(0, 1, range(0, 10), 100, RED_SHORTS) + person(
        0, 1, range(10, 20), 600, RED_SHORTS
    )
    assert cut_points(track, CONFIG) == [10]


def test_a_steady_track_is_left_whole() -> None:
    track = person(0, 1, range(0, 30), 100, RED_SHORTS, kit=RED_KIT)
    assert cut_points(track, CONFIG) == []
    assert ids(split_switches(track, CONFIG)) == {1: list(range(30))}


def test_one_odd_frame_is_not_a_switch() -> None:
    # A glove covers the chest for one frame: the median ignores it.
    track = person(0, 1, range(0, 20), 100, RED_SHORTS, kit=RED_KIT)
    track[8]["torso_red"], track[8]["torso_blue"] = BLUE_KIT
    assert cut_points(track, CONFIG) == []


def test_new_ids_are_above_the_highest_in_the_shot_and_keep_bytetrack_id() -> None:
    mixed = switching(
        0,
        1,
        person(0, 1, range(0, 10), 400, RED_SHORTS, kit=RED_KIT),
        person(0, 1, range(10, 20), 400, BLUE_SHORTS, kit=BLUE_KIT),
    )
    other = person(0, 7, range(0, 20), 50, BLUE_SHORTS)
    out = split_switches(mixed + other, CONFIG)
    assert sorted(ids(out)) == [1, 7, 8]
    assert all(d["bytetrack_id"] in (1, 7) for d in out)
    assert {d["bytetrack_id"] for d in out if d["track_id"] == 8} == {1}
    assert is_split(out) and not is_split(mixed)


def test_split_pieces_go_to_the_right_corners() -> None:
    # Red and blue overlap at frame 10 and ByteTrack swaps their IDs.
    detections = switching(
        0,
        1,
        person(0, 1, range(0, 10), 100, RED_SHORTS, kit=RED_KIT),
        person(0, 1, range(10, 20), 140, BLUE_SHORTS, kit=BLUE_KIT),
    ) + switching(
        0,
        2,
        person(0, 2, range(0, 10), 140, BLUE_SHORTS, kit=BLUE_KIT),
        person(0, 2, range(10, 20), 100, RED_SHORTS, kit=RED_KIT),
    )
    right = ([1, 4], [2, 3])  # the red halves, and the blue halves
    unsplit = assign_corners(summarise_tracks(detections), CONFIG)["shots"][0]
    assert (unsplit["red"], unsplit["blue"]) != right  # each track is half wrong
    split = assign_corners(summarise_tracks(split_switches(detections, CONFIG)), CONFIG)["shots"][0]
    assert (split["red"], split["blue"]) == right


def test_assign_splits_older_detections_once_and_saves_them(data_dir: Path) -> None:
    out = data_dir / "processed" / "fight"
    out.mkdir(parents=True)
    detections = switching(
        0,
        1,
        person(0, 1, range(0, 10), 100, RED_SHORTS, kit=RED_KIT),
        person(0, 1, range(10, 20), 100, BLUE_SHORTS, kit=BLUE_KIT),
    ) + person(0, 2, range(0, 20), 500, BLUE_SHORTS, kit=BLUE_KIT)
    frames = [{"index": i, "timestamp_ms": i * 100, "shot": 0, "skipped": False} for i in range(20)]
    (out / "detections.json").write_text(json.dumps({"frames": frames, "detections": detections}))
    assign("fight", CONFIG)
    saved = json.loads((out / "detections.json").read_text())["detections"]
    assert is_split(saved)
    assert sorted({d["track_id"] for d in saved}) == [1, 2, 3]
    tracks = json.loads((out / "tracks.json").read_text())
    assert tracks["shots"][0]["red"] == [1]
