"""Training windows from synthetic keypoints and tags. No real footage or tags."""

import json
from pathlib import Path
from typing import Any

import pytest

from strikelens_cv.cli import main
from strikelens_cv.strikes import (
    WindowsConfig,
    build_windows,
    cut_window,
    fight_windows,
    load_windows_config,
    normalise,
    sample_times,
    split_for,
    summary,
)
from strikelens_cv.strikes.config import DEFAULT_WINDOWS_CONFIG

CONFIG = WindowsConfig()
BOX = [100.0, 100.0, 200.0, 300.0]  # centre (150, 200), height 200


def kp(value: float = 0.0) -> list[list[float]]:
    """33 keypoints, all at the box centre shifted by `value` pixels."""
    return [[150.0 + value, 200.0, 0.0, 0.9] for _ in range(33)]


def frames(until_ms: int = 20_000, step: int = 100, gaps: range = range(0)) -> list[dict[str, Any]]:
    """Keypoint frames every `step` ms; frames whose ms are in `gaps` have none."""
    return [
        {
            "index": t // step,
            "timestamp_ms": t,
            "box": BOX,
            "keypoints": None if t in gaps else kp(t / 1000),
            "missing": "no_pose" if t in gaps else None,
        }
        for t in range(0, until_ms, step)
    ]


def tag(
    id_: str, ms: int, fighter: str = "red", status: str = "confirmed", weapon: str | None = "jab"
) -> dict[str, Any]:
    return {"id": id_, "timestamp_ms": ms, "fighter": fighter, "weapon": weapon, "status": status}


def test_normalise_to_the_box() -> None:
    assert normalise([[150, 200, 20, 0.95], [200, 100, 0, 0.5]], BOX) == [
        [0.0, 0.0, 0.1, 0.95],
        [0.25, -0.5, 0.0, 0.5],
    ]


def test_sample_times_span_the_window() -> None:
    times = sample_times(5000, CONFIG)
    assert len(times) == 16
    assert times[0] == 4400 and times[-1] == 5400


def test_cut_window_uses_the_nearest_frame() -> None:
    samples = cut_window(frames(), 5000, CONFIG)
    assert len(samples) == 16
    first = samples[0]
    assert first is not None
    assert first[0][0] == pytest.approx(4.4 / 200)  # the 4.4 s frame, shifted 4.4 px


def test_missing_keypoints_stay_missing() -> None:
    # Frames 4.4-4.6 s have no keypoints. Samples are 1000 / 15 ms apart, so the
    # first four (4.4, 4.47, 4.53, 4.6 s) land on them.
    samples = cut_window(frames(gaps=range(4400, 4700, 100)), 5000, CONFIG)
    assert samples[:4] == [None] * 4
    assert all(s is not None for s in samples[4:])


def test_a_sample_far_from_any_frame_is_missing() -> None:
    sparse = [f for f in frames() if f["timestamp_ms"] % 1000 == 0]  # one frame a second
    assert any(s is None for s in cut_window(sparse, 5000, CONFIG))


def test_positive_rejected_and_background_windows() -> None:
    tags = [
        tag("a", 5000, weapon="kick"),
        tag("b", 9000, fighter="blue", weapon="jab"),
        tag("c", 12_000, status="rejected", weapon=None),
        tag("d", 14_000, status="pending", weapon="hook"),  # not reviewed: not used
    ]
    windows = fight_windows("f", "train", {"red": frames(), "blue": frames()}, tags, CONFIG)
    strikes = [(w["label"], w["fighter"], w["tag_id"]) for w in windows if w["kind"] == "strike"]
    assert strikes == [("kick", "red", "a"), ("jab", "blue", "b")]
    assert [(w["label"], w["tag_id"]) for w in windows if w["kind"] == "rejected"] == [
        ("none", "c")
    ]
    background = [w for w in windows if w["kind"] == "background"]
    assert len(background) == 4  # 2 per positive, per fighter
    for w in background:
        own = [t["timestamp_ms"] for t in tags if t["fighter"] == w["fighter"]]
        assert all(abs(w["center_ms"] - t) >= CONFIG.negative_gap_ms for t in own)
        assert w["label"] == "none" and w["tag_id"] is None


def test_windows_with_too_many_missing_samples_are_dropped() -> None:
    tags = [tag("a", 5000)]
    windows = fight_windows(
        "f", "train", {"red": frames(gaps=range(4000, 6000, 100))}, tags, CONFIG
    )
    assert [w for w in windows if w["kind"] == "strike"] == []


def test_the_same_inputs_give_the_same_windows() -> None:
    tags = [tag("a", 5000), tag("b", 15_000)]
    args = ("f", "train", {"red": frames(), "blue": frames()}, tags, CONFIG)
    assert fight_windows(*args) == fight_windows(*args)  # type: ignore[arg-type]


def test_split_is_stable_and_follows_the_share() -> None:
    names = [f"fight-{i}" for i in range(200)]
    assert [split_for(n, 0.2) for n in names] == [split_for(n, 0.2) for n in names]
    held_out = sum(split_for(n, 0.2) == "validation" for n in names)
    assert 20 <= held_out <= 60
    assert all(split_for(n, 0) == "train" for n in names)


def test_summary_counts_per_split_and_label() -> None:
    windows = fight_windows("f", "train", {"red": frames()}, [tag("a", 5000)], CONFIG)
    assert summary(windows) == {"train": {"jab": 1, "none": 2}}


def write_fight(
    data_dir: Path, name: str, fmt: str = "mediapipe_pose_33", tags: Any = None
) -> None:
    out = data_dir / "processed" / name
    (out / "keypoints").mkdir(parents=True)
    for corner in ("red", "blue"):
        data = {"format": fmt, "landmarks": [f"p{i}" for i in range(33)], "frames": frames()}
        (out / "keypoints" / f"{corner}.json").write_text(json.dumps(data))
    if tags is not None:
        (out / "tags.json").write_text(json.dumps(tags))


def test_build_windows_writes_lines_and_a_manifest(data_dir: Path) -> None:
    write_fight(data_dir, "one", tags=[tag("a", 5000), tag("b", 8000, fighter="blue")])
    write_fight(data_dir, "two", tags={"tags": [tag("c", 6000, weapon="teep")]})
    result = build_windows("v1", ["one", "two"], CONFIG)
    assert result.out_dir == data_dir / "labels" / "windows" / "v1"
    lines = (result.out_dir / "windows.jsonl").read_text().splitlines()
    assert len(lines) == sum(sum(c.values()) for c in result.manifest["counts"].values())
    manifest = json.loads((result.out_dir / "manifest.json").read_text())
    assert manifest["format"] == "mediapipe_pose_33"
    assert len(manifest["landmarks"]) == 33
    assert set(manifest["fights"]) == {"one", "two"}
    # A fight's windows are all in its split.
    for line in lines:
        window = json.loads(line)
        assert window["split"] == manifest["fights"][window["fight"]]


def test_mixed_keypoint_formats_are_refused(data_dir: Path) -> None:
    write_fight(data_dir, "one", tags=[])
    write_fight(data_dir, "two", fmt="rtmpose_17", tags=[])
    with pytest.raises(ValueError, match="different keypoint formats"):
        build_windows("v1", ["one", "two"], CONFIG)


def test_missing_tags_explain_how_to_save_them(data_dir: Path) -> None:
    write_fight(data_dir, "one")
    with pytest.raises(FileNotFoundError, match="save the fight's tags"):
        build_windows("v1", ["one"], CONFIG)


def test_cli(data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_fight(data_dir, "one", tags=[tag("a", 5000)])
    assert main(["windows", "--fight", "one", "--name", "v1"]) == 0
    printed = capsys.readouterr().out
    assert "windows (jab 1, none 2)" in printed
    assert "All fights are in" in printed
    assert main(["windows", "--fight", "nothing", "--name", "v1"]) == 1


def test_config() -> None:
    assert load_windows_config(DEFAULT_WINDOWS_CONFIG) == CONFIG
    for bad in (
        {"samples": 1},
        {"before_ms": 0, "after_ms": 0},
        {"max_missing": 1},
        {"validation_share": 1},
    ):
        with pytest.raises(ValueError):
            WindowsConfig(**bad)  # type: ignore[arg-type]
