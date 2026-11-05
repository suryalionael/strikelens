"""Ingest a tiny synthetic video for real. Runs only where FFmpeg and the ingest extra
are installed (`uv sync --extra ingest`); CI installs no extras, so it skips there.
The video is generated here: no real footage is involved."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from strikelens_cv.cli import main

pytest.importorskip("scenedetect", reason="needs the ingest extra")
FFMPEG = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(FFMPEG is None, reason="needs FFmpeg")


@pytest.fixture
def synthetic_video(tmp_path: Path) -> Path:
    """2 s of red, a hard cut, then 2 s of blue, at 30 fps."""
    path = tmp_path / "synthetic.mp4"
    assert FFMPEG is not None
    subprocess.run(
        [
            FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=160x90:r=30:d=2",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=160x90:r=30:d=2",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1[v]",
            "-map",
            "[v]",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
    )
    return path


def test_ingest_cli_on_a_synthetic_video(
    synthetic_video: Path, data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["ingest", str(synthetic_video), "--fight", "Synthetic"]) == 0
    assert "40 frames and 1 cut" in capsys.readouterr().out

    out = data_dir / "processed" / "synthetic"
    manifest = json.loads((out / "frames.json").read_text())
    stamps = [f["timestamp_ms"] for f in manifest["frames"]]
    assert stamps == [i * 100 for i in range(40)]
    assert all((out / "frames" / f["file"]).is_file() for f in manifest["frames"])

    cuts = json.loads((out / "cuts.json").read_text())
    starts = [s["start_ms"] for s in cuts["shots"]]
    assert len(starts) == 2
    # The cut is at 2 s; allow one source frame either side.
    assert abs(starts[1] - 2_000) <= 34
    assert cuts["shots"][-1]["end_ms"] == pytest.approx(4_000, abs=34)
