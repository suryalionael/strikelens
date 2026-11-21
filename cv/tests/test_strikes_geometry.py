"""The geometry strike model (ported from mma-vision) on synthetic stick figures.

Red stands on the left facing blue. Torso height is 100 px, so distances in the
model's torso units are pixels / 100. Frames are 30 fps unless a test says not.
"""

from typing import Any

import pytest

from strikelens_cv.strikes.geometry import (
    JOINTS,
    GeometryConfig,
    Series,
    build_series,
    detect,
    weapon_for,
)
from strikelens_cv.strikes.suggest import (
    geometry_candidates,
    geometry_peaks,
    load_geometry_config,
)

STEP_MS = 33
CONFIG = GeometryConfig()

Pose = dict[str, tuple[float, float]]

RED: Pose = {
    "nose": (300, 350),
    "l_eye": (295, 345),
    "r_eye": (305, 345),
    "l_ear": (290, 350),
    "r_ear": (310, 350),
    "l_shoulder": (280, 400),
    "r_shoulder": (320, 400),  # nearer blue: the right hand leads
    "l_elbow": (290, 440),
    "r_elbow": (340, 430),
    "l_wrist": (300, 390),
    "r_wrist": (335, 390),
    "l_hip": (290, 500),
    "r_hip": (320, 500),
    "l_knee": (290, 600),
    "r_knee": (330, 600),
    "l_ankle": (295, 700),
    "r_ankle": (345, 700),
}


# Blue is red mirrored about x = 380, so blue's nose is at x = 460, facing red: hips
# 1.5 torso-heights apart, punching range.
BLUE: Pose = {k: (760 - x, y) for k, (x, y) in RED.items()}


def frame(t: int, pose: Pose) -> dict[str, Any]:
    keypoints = [[0.0, 0.0, 0.0, 0.0] for _ in range(33)]
    for name, (x, y) in pose.items():
        keypoints[JOINTS[name]] = [x, y, 0.0, 0.99]
    xs, ys = [p[0] for p in pose.values()], [p[1] for p in pose.values()]
    return {"timestamp_ms": t, "keypoints": keypoints, "box": [min(xs), min(ys), max(xs), max(ys)]}


def fight(red_moves: dict[int, Pose], n: int = 40) -> list[dict[str, Any]]:
    """Run the model on n frames where red's pose changes at the given frame numbers
    (a change holds until the next one) and blue stands still."""
    red_frames, blue_frames, pose = [], [], dict(RED)
    for i in range(n):
        pose = {**pose, **red_moves.get(i, {})}
        red_frames.append(frame(i * STEP_MS, pose))
        blue_frames.append(frame(i * STEP_MS, BLUE))
    shots = [{"start_ms": 0, "end_ms": n * STEP_MS}]
    return geometry_candidates({"red": red_frames, "blue": blue_frames}, shots, CONFIG)


def accepted(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [c for c in candidates if not c["rejected_by"]]


def punch(to: tuple[float, float], elbow: tuple[float, float]) -> dict[int, Pose]:
    """Red's lead hand goes out over two frames, holds, and comes back."""
    mid = ((335 + to[0]) / 2, (390 + to[1]) / 2)
    out = {"r_wrist": to, "r_elbow": elbow}
    guard = {"r_wrist": RED["r_wrist"], "r_elbow": RED["r_elbow"]}
    return {
        10: {"r_wrist": mid, "r_elbow": (350, 410)},
        11: out,
        14: {"r_wrist": mid, "r_elbow": (350, 410)},
        15: guard,
    }


def test_the_stick_figures_face_each_other() -> None:
    assert BLUE["nose"] == (460, 350)
    assert RED["r_shoulder"][0] < BLUE["r_shoulder"][0]


def test_a_straight_punch_to_the_head_lands() -> None:
    [strike] = accepted(fight(punch(to=(440, 370), elbow=(380, 385))))
    assert strike["fighter"] == "red" and strike["kind"] == "punch"
    assert strike["target"] == "head" and strike["landed"] is True
    assert strike["weapon"] == "jab"  # the lead hand


def test_a_short_feint_is_not_a_strike() -> None:
    candidates = fight(punch(to=(360, 380), elbow=(345, 400)))
    assert accepted(candidates) == []
    assert {c["rejected_by"] for c in candidates} <= {"not_extended", "no_reach", "no_travel"}


def test_a_step_forward_is_not_a_kick() -> None:
    step = {
        10: {"r_ankle": (372, 700), "r_knee": (348, 600)},
        11: {"r_ankle": (400, 700), "r_knee": (365, 600)},
    }
    assert accepted(fight(step)) == []


def test_a_kick_that_lifts_the_foot_into_the_body_lands() -> None:
    kick = {
        10: {"r_ankle": (380, 623), "r_knee": (348, 587)},
        11: {"r_ankle": (415, 547), "r_knee": (372, 566)},
        12: {"r_ankle": (450, 470), "r_knee": (395, 545)},
        16: {"r_ankle": RED["r_ankle"], "r_knee": RED["r_knee"]},
    }
    [strike] = accepted(fight(kick))
    assert strike["kind"] == "kick" and strike["weapon"] == "kick"
    assert strike["target"] == "body" and strike["landed"] is True


def test_nothing_moves_nothing_counts() -> None:
    assert fight({}) == []


def test_impossible_limbs_are_dropped() -> None:
    times = [0]
    pose = {**RED, "r_wrist": (700, 390)}  # 360 px from the elbow: longer than an arm
    series = build_series(times, {0: frame(0, pose)}, [False], CONFIG)
    assert series.pt("r_wrist")[0] is None
    assert series.pt("l_wrist")[0] is not None
    assert series.scale[0] == pytest.approx(100, abs=1)


def test_unsure_joints_are_unknown() -> None:
    f = frame(0, RED)
    f["keypoints"][JOINTS["r_wrist"]][3] = 0.1
    series = build_series([0], {0: f}, [False], CONFIG)
    assert series.pt("r_wrist")[0] is None


def test_short_gaps_are_filled_and_long_ones_are_not() -> None:
    times = [0, 100, 200, 300, 400, 500, 600, 700]
    frames = {t: frame(t, RED) for t in times}
    frames[100] = {"timestamp_ms": 100, "keypoints": None, "box": None}
    for t in (400, 500, 600):
        frames[t] = {"timestamp_ms": t, "keypoints": None, "box": None}
    config = GeometryConfig(smooth_alpha_30fps=1)
    series = build_series(times, frames, [False] * len(times), config)
    assert series.pt("nose")[1] == pytest.approx(RED["nose"])  # one 100 ms gap
    assert series.pt("nose")[4] is None  # 300 ms is longer than gap_ms


def test_the_gates_drop_a_one_frame_keypoint_jump() -> None:
    from strikelens_cv.strikes.geometry import _gate

    base = {
        "time_ms": 1000,
        "peak_ms": 1000,
        "fighter": "red",
        "limb": "r_wrist",
        "kind": "punch",
        "weapon": "jab",
        "target": "head",
        "landed": False,
        "confidence": 0.0,
        "speed": 10.0,
        "toward": 0.9,
        "extension": 0.9,
        "travel": 0.7,
        "reach": 0.5,
        "land_dist": 0.1,
        "head_react": 0.0,
        "body_react": 0.0,
        "range": 1.2,
        "support": 0,
        "in_combo": False,
        "in_clinch": False,
        "rejected_by": "",
        "near_cut": False,
    }
    [jump] = _gate([dict(base)], CONFIG)
    assert jump["rejected_by"] == "keypoint_jump"
    [cut] = _gate([{**base, "support": 2, "near_cut": True}], CONFIG)
    assert cut["rejected_by"] == "camera_cut"
    first, second = _gate(
        [{**base, "support": 2}, {**base, "support": 2, "time_ms": 1100, "peak_ms": 1100}],
        CONFIG,
    )
    assert first["rejected_by"] == "" and first["landed"] is True
    assert second["rejected_by"] == "too_soon"  # 100 ms after the first, under min_gap_ms


def test_lead_hand_is_a_jab_and_rear_hand_a_cross() -> None:
    series = Series([0], {k: [v] for k, v in RED.items()}, [100.0])
    blue_center = (457.5, 450.0)
    assert weapon_for("punch", "r_wrist", series, blue_center, 0) == "jab"
    assert weapon_for("punch", "l_wrist", series, blue_center, 0) == "cross"
    assert weapon_for("kick", "l_ankle", series, blue_center, 0) == "kick"


def test_accepted_candidates_become_prefilled_peaks() -> None:
    candidates = [
        {"rejected_by": "", "fighter": "red", "time_ms": 1000, "confidence": 0.8,
         "weapon": "jab", "landed": True, "target": "head"},
        {"rejected_by": "", "fighter": "blue", "time_ms": 2000, "confidence": 0.4,
         "weapon": "kick", "landed": False, "target": "legs"},
        {"rejected_by": "slow", "fighter": "blue", "time_ms": 3000, "confidence": 0.0,
         "weapon": "cross", "landed": False, "target": "body"},
    ]  # fmt: skip
    peaks = geometry_peaks(candidates)
    assert peaks["red"] == [
        {"timestamp_ms": 1000, "score": 0.8, "weapon": "jab", "outcome": "landed", "target": "head"}
    ]
    assert [p["outcome"] for p in peaks["blue"]] == ["missed"]


def test_the_shipped_geometry_settings_load_and_bad_ones_are_refused() -> None:
    assert load_geometry_config() == GeometryConfig()
    with pytest.raises(ValueError, match="combo_relax"):
        GeometryConfig(combo_relax=0)
    with pytest.raises(ValueError, match="punch_speed"):
        GeometryConfig(punch_speed=-1)


def test_detect_runs_on_series_directly() -> None:
    times = [i * STEP_MS for i in range(5)]
    series = {
        corner: build_series(times, {t: frame(t, pose) for t in times}, [False] * 5, CONFIG)
        for corner, pose in (("red", RED), ("blue", BLUE))
    }
    assert detect(series, [False] * 5, CONFIG) == []
