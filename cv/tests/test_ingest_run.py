"""The ingest runner with FFmpeg and PySceneDetect replaced, so it runs without extras."""

import json
from pathlib import Path

import pytest

from strikelens_cv.ingest import IngestConfig, ingest, run
from strikelens_cv.ingest.frames import FrameEntry


@pytest.fixture
def video(tmp_path: Path) -> Path:
    path = tmp_path / "private" / "fight.mp4"
    path.parent.mkdir()
    path.write_bytes(b"not really a video")
    return path


@pytest.fixture
def fake_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_extract(_video: Path, frames_dir: Path, config: IngestConfig) -> list[FrameEntry]:
        frames_dir.mkdir(parents=True, exist_ok=True)
        (frames_dir / "000000.jpg").write_bytes(b"jpg")
        return [{"index": 0, "file": "000000.jpg", "timestamp_ms": 0}]

    monkeypatch.setattr(run, "extract_frames", fake_extract)
    monkeypatch.setattr(run, "detect_scenes", lambda *_: ([(0.0, 2.0), (2.0, 4.0)], 4_000))


@pytest.mark.usefixtures("fake_tools")
def test_writes_frames_cuts_and_settings(video: Path, data_dir: Path) -> None:
    result = ingest(video, "Test Fight 1", IngestConfig(fps=10))
    out = data_dir / "processed" / "test-fight-1"
    assert result.out_dir == out
    assert json.loads((out / "frames.json").read_text()) == {
        "fps": 10,
        "frames": [{"index": 0, "file": "000000.jpg", "timestamp_ms": 0}],
    }
    assert json.loads((out / "cuts.json").read_text()) == {
        "duration_ms": 4_000,
        "shots": [
            {"index": 0, "start_ms": 0, "end_ms": 2_000},
            {"index": 1, "start_ms": 2_000, "end_ms": 4_000},
        ],
    }
    settings = json.loads((out / "ingest.json").read_text())
    assert settings["config"]["fps"] == 10
    assert settings["frame_count"] == 1
    assert settings["shot_count"] == 2


@pytest.mark.usefixtures("fake_tools")
def test_records_only_the_video_file_name(video: Path, data_dir: Path) -> None:
    ingest(video, "fight", IngestConfig())
    settings = (data_dir / "processed" / "fight" / "ingest.json").read_text()
    assert json.loads(settings)["video_file"] == "fight.mp4"
    assert "private" not in settings


@pytest.mark.usefixtures("fake_tools")
def test_does_not_overwrite_frames_unless_asked(video: Path, data_dir: Path) -> None:
    ingest(video, "fight", IngestConfig())
    with pytest.raises(FileExistsError, match="--overwrite"):
        ingest(video, "fight", IngestConfig())
    stale = data_dir / "processed" / "fight" / "frames" / "999999.jpg"
    stale.write_bytes(b"old")
    ingest(video, "fight", IngestConfig(), overwrite=True)
    assert not stale.exists()


def test_missing_video(data_dir: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ingest(data_dir / "nope.mp4", "fight", IngestConfig())
