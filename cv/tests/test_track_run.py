"""The track runner's file handling, with YOLO left out (no extras needed)."""

import json
from pathlib import Path

import pytest

from strikelens_cv.cli import main
from strikelens_cv.track import TrackConfig, assign, label_frames, swaps, track, weights_path
from tests.track_cases import BLUE_SHORTS, RED_SHORTS, person


@pytest.fixture
def models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "models"
    root.mkdir()
    monkeypatch.setenv("STRIKELENS_MODELS_DIR", str(root))
    return root


def write_detections(data_dir: Path, rounds: list[dict[str, int]] | None = None) -> Path:
    """detections.json for two shots. Without `rounds`, it has no "rounds" key (old files)."""
    out = data_dir / "processed" / "fight"
    out.mkdir(parents=True)
    detections = (
        person(0, 1, range(0, 5), 50, RED_SHORTS)
        + person(0, 2, range(0, 5), 400, BLUE_SHORTS)
        + person(1, 1, range(5, 10), 400, RED_SHORTS)
        + person(1, 2, range(5, 10), 50, BLUE_SHORTS)
    )
    frames = [
        {"index": i, "timestamp_ms": i * 100, "shot": 0 if i < 5 else 1, "skipped": False}
        for i in range(10)
    ]
    data: dict[str, object] = {"frames": frames, "detections": detections}
    if rounds is not None:
        data["rounds"] = rounds
    (out / "detections.json").write_text(json.dumps(data))
    return out


def test_label_frames_by_shot_and_segment() -> None:
    frames = [{"index": i, "file": f"{i:06}.jpg", "timestamp_ms": i * 500} for i in range(5)]
    shots = [
        {"index": 0, "start_ms": 0, "end_ms": 1_000},
        {"index": 1, "start_ms": 1_000, "end_ms": 2_000},
    ]
    segments = [{"kind": "replay", "start_ms": 1_500, "end_ms": 1_700}]
    labelled = label_frames(frames, shots, segments)  # type: ignore[arg-type]
    assert [(f["shot"], f["skipped"]) for f in labelled] == [
        (0, False),
        (0, False),
        (1, False),  # on the cut: the new shot
        (1, True),
        (1, False),  # at the very end of the file: the last shot
    ]


def test_label_frames_skips_outside_rounds() -> None:
    frames = [{"index": i, "file": f"{i:06}.jpg", "timestamp_ms": i * 500} for i in range(10)]
    shots = [{"index": 0, "start_ms": 0, "end_ms": 5_000}]
    rounds = [
        {"number": 1, "start_ms": 500, "end_ms": 1_500},
        {"number": 2, "start_ms": 3_000, "end_ms": 4_000},
    ]
    segments = [{"kind": "replay", "start_ms": 3_500, "end_ms": 4_000}]
    labelled = label_frames(frames, shots, segments, rounds)  # type: ignore[arg-type]
    assert [f["timestamp_ms"] for f in labelled if not f["skipped"]] == [
        500,
        1_000,
        1_500,  # round end is inclusive
        3_000,
        # 3_500 is in round 2 but inside a replay
        4_000,  # the replay's end is exclusive, the round's inclusive
    ]


def test_assign_writes_tracks(data_dir: Path) -> None:
    out = write_detections(data_dir)
    result = assign("fight", TrackConfig(min_track_frames=3))
    written = json.loads((out / "tracks.json").read_text())
    assert written["seeded_by"] == "left_is_red"
    assert written["corrections"] is None
    assert written["rounds"] == []  # an old detections.json: the whole video
    assert len(written["frames"]) == 10
    assert written["frames"][7]["red"] == [400.0, 100.0, 500.0, 400.0]  # red moved right
    assert result.assignment["shots"][1]["red"] == [1]


def test_assign_keeps_the_rounds_from_detections(data_dir: Path) -> None:
    rounds = [{"number": 1, "start_ms": 0, "end_ms": 900}]
    out = write_detections(data_dir, rounds)
    result = assign("fight", TrackConfig(min_track_frames=3))
    assert result.rounds == rounds
    assert json.loads((out / "tracks.json").read_text())["rounds"] == rounds


def test_swaps_against_corrections(data_dir: Path, tmp_path: Path) -> None:
    write_detections(data_dir)
    corrections = tmp_path / "track-corrections.json"
    # The truth: the fighter on the right in shot 0 was red, so the guess was wrong.
    corrections.write_text(
        json.dumps({"corrections": [{"shot": 0, "track_id": 2, "corner": "red"}]})
    )
    report = swaps("fight", TrackConfig(min_track_frames=3), corrections)
    assert report == {"swaps": 1, "swapped_frames": 10, "compared_frames": 10}


def test_weights_must_be_in_models(models: Path) -> None:
    with pytest.raises(FileNotFoundError, match="ultralytics/assets"):
        weights_path(TrackConfig())
    (models / "yolo11n.pt").write_bytes(b"weights")
    assert weights_path(TrackConfig()) == models / "yolo11n.pt"


def test_track_needs_ingest_output(data_dir: Path) -> None:
    with pytest.raises(FileNotFoundError, match="ingest first"):
        track("fight", TrackConfig())


class TestCli:
    def test_assign_needs_detections(
        self, data_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["assign", "--fight", "fight"]) == 1
        assert "run strikelens-cv track first" in capsys.readouterr().err

    def test_assign_reports_and_warns_about_the_guess(
        self, data_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        write_detections(data_dir)
        assert main(["assign", "--fight", "fight"]) == 0
        out = capsys.readouterr().out
        assert "10 of 10 frames have a fighter, 2 shots, 0 uncertain" in out
        assert "guessed as the fighter on the left" in out
        assert "No rounds in fight.json: tracked the whole video" in out

    def test_assign_reports_the_rounds(
        self, data_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        write_detections(data_dir, [{"number": 1, "start_ms": 0, "end_ms": 400}])
        assert main(["assign", "--fight", "fight"]) == 0
        out = capsys.readouterr().out
        assert "Tracked inside 1 round: 5 frames." in out
        assert "No rounds" not in out

    def test_swaps_needs_corrections(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            main(["swaps", "--fight", "fight"])
        assert "--corrections" in capsys.readouterr().err

    def test_track_reports_missing_weights(
        self, data_dir: Path, models: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        out = data_dir / "processed" / "fight"
        out.mkdir(parents=True)
        (out / "frames.json").write_text('{"fps": 10, "frames": []}')
        (out / "cuts.json").write_text('{"duration_ms": 0, "shots": []}')
        # Checked before YOLO is imported, so this works without the detect extra.
        assert main(["track", "--fight", "fight"]) == 1
        assert "no YOLO weights" in capsys.readouterr().err
