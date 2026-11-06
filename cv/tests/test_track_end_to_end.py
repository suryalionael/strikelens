"""Run YOLO and ByteTrack for real on a synthetic clip.

Skips unless the detect extra and models/<weights> are installed, so it never runs
in CI. The people clip is made from zidane.jpg, a sample photo that ships inside
the ultralytics package, so no footage is involved.
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


@pytest.mark.usefixtures("data_dir")
def test_track_two_people(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from ultralytics.utils import ASSETS

    monkeypatch.setenv("STRIKELENS_MODELS_DIR", str(WEIGHTS.parent))
    video = tmp_path / "two-people.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-i",
            str(ASSETS / "zidane.jpg"),
            "-t",
            "2",
            "-r",
            "10",
            "-vf",
            "scale=640:-2",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        check=True,
    )
    ingest(video, "two-people", IngestConfig(fps=5))
    # Filter and kit off: this checks tracking. Whether they are right needs ring
    # footage (a red tie in the chest band could pass as kit).
    config = TrackConfig(min_track_frames=3, referee_filter=False, kit_corner=False)
    result = track("two-people", config)

    assert result.assignment["seeded_by"] == "left_is_red"
    with_both = [f for f in result.frames if f["red"] and f["blue"]]
    assert len(with_both) >= 8  # of 10 frames
    first = with_both[0]
    assert first["red"] is not None and first["blue"] is not None
    assert first["red"][0] < first["blue"][0]  # red is the one on the left
    # Every box gets the chest measures for the referee filter and the kit colour.
    detections = json.loads((result.out_dir / "detections.json").read_text())["detections"]
    assert all("torso_skin" in d and "torso_red" in d for d in detections)
