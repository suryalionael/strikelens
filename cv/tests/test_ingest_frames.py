import subprocess
from pathlib import Path

import pytest

from strikelens_cv.ingest import frames
from strikelens_cv.ingest.config import IngestConfig


def test_ffmpeg_command_extracts_at_the_configured_rate() -> None:
    command = frames.ffmpeg_command(
        Path("fight.mp4"), Path("out"), IngestConfig(fps=12.5, jpeg_quality=4), "ffmpeg"
    )
    assert command[:2] == ["ffmpeg", "-hide_banner"]
    assert command[command.index("-i") + 1] == "fight.mp4"
    assert command[command.index("-vf") + 1] == "fps=12.5"
    assert command[command.index("-q:v") + 1] == "4"
    # Files are named after their frame number at the output rate.
    assert command[command.index("-frame_pts") + 1] == "1"
    assert command[-1] == str(Path("out") / "%06d.jpg")


@pytest.mark.parametrize(
    ("index", "fps", "ms"),
    [(0, 10, 0), (1, 10, 100), (36_000, 10, 3_600_000), (3, 29.97, 100), (1, 3, 333)],
)
def test_frame_timestamp(index: int, fps: float, ms: int) -> None:
    assert frames.frame_timestamp_ms(index, fps) == ms


def test_frame_timestamp_rejects_negative_index() -> None:
    with pytest.raises(ValueError):
        frames.frame_timestamp_ms(-1, 10)


def test_manifest_lists_frames_in_order_with_times(tmp_path: Path) -> None:
    for index in (10, 0, 2):
        (tmp_path / f"{index:06d}.jpg").write_bytes(b"jpg")
    (tmp_path / "notes.txt").write_text("ignored")
    assert frames.frame_manifest(tmp_path, fps=10) == [
        {"index": 0, "file": "000000.jpg", "timestamp_ms": 0},
        {"index": 2, "file": "000002.jpg", "timestamp_ms": 200},
        {"index": 10, "file": "000010.jpg", "timestamp_ms": 1000},
    ]


def test_missing_ffmpeg_gives_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(frames.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="FFmpeg is not installed"):
        frames.ffmpeg_binary()


def test_ffmpeg_failure_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(frames, "ffmpeg_binary", lambda: "ffmpeg")
    monkeypatch.setattr(
        frames.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "Invalid data found"),
    )
    with pytest.raises(RuntimeError, match="FFmpeg failed: Invalid data found"):
        frames.extract_frames(tmp_path / "bad.mp4", tmp_path / "frames", IngestConfig())
