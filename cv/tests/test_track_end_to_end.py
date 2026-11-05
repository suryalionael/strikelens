"""Run YOLO and ByteTrack for real on a synthetic clip.

Skips unless the detect extra and models/<weights> are installed, so it never runs
in CI. The clip has no people, so this checks the plumbing, not the accuracy.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from strikelens_cv.ingest import IngestConfig, ingest
from strikelens_cv.paths import REPO_ROOT
from strikelens_cv.track import TrackConfig, track

pytest.importorskip("ultralytics")
pytest.importorskip("scenedetect")
WEIGHTS = REPO_ROOT / "models" / TrackConfig().weights
if shutil.which("ffmpeg") is None or not WEIGHTS.is_file():
    pytest.skip("needs FFmpeg and YOLO weights in models/", allow_module_level=True)


def test_track_a_synthetic_clip(
    tmp_path: Path, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STRIKELENS_MODELS_DIR", str(WEIGHTS.parent))
    video = tmp_path / "synthetic.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=320x240:rate=10",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        check=True,
    )
    ingest(video, "synthetic", IngestConfig(fps=5))
    result = track("synthetic", TrackConfig())
    written = json.loads((result.out_dir / "tracks.json").read_text())
    assert len(written["frames"]) == 10
    assert (result.out_dir / "detections.json").is_file()
