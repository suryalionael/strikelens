"""Render a real MP4 from synthetic frames and made-up tracks and keypoints.

Skips unless FFmpeg, ffprobe, and the ingest extra (OpenCV) are installed, so it
never runs in CI. No footage is involved.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from strikelens_cv.overlay import OverlayConfig, overlay

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")
FFPROBE = shutil.which("ffprobe")
if shutil.which("ffmpeg") is None or FFPROBE is None:
    pytest.skip("needs FFmpeg and ffprobe", allow_module_level=True)


def write_fight(data_dir: Path) -> Path:
    out = data_dir / "processed" / "fight"
    (out / "frames").mkdir(parents=True)
    (out / "keypoints").mkdir()
    frames, labelled, tracks, poses = [], [], [], []
    for i in range(8):
        name = f"{i:06}.jpg"
        cv2.imwrite(str(out / "frames" / name), np.full((240, 320, 3), 90, dtype=np.uint8))
        frames.append({"index": i, "file": name, "timestamp_ms": i * 200})
        labelled.append({"index": i, "timestamp_ms": i * 200, "shot": 0, "skipped": i == 2})
        box = [40.0 + i, 40.0, 140.0 + i, 220.0]
        tracks.append({"index": i, "timestamp_ms": i * 200, "red": box, "blue": None})
        keypoints = [[60.0 + i, 40.0 + 5 * k, 0.0, 0.9] for k in range(33)]
        poses.append({"index": i, "timestamp_ms": i * 200, "box": box, "keypoints": keypoints})
    detections = [
        {"frame": i, "shot": 0, "track_id": 1, "box": tracks[i]["red"], "confidence": 0.9}
        for i in range(8)
    ]
    shots = [{"shot": 0, "red": [1], "blue": [], "dropped": [], "uncertain": False}]
    (out / "frames.json").write_text(json.dumps({"fps": 5, "frames": frames}))
    (out / "detections.json").write_text(json.dumps({"frames": labelled, "detections": detections}))
    (out / "tracks.json").write_text(json.dumps({"shots": shots, "frames": tracks}))
    (out / "keypoints" / "red.json").write_text(json.dumps({"frames": poses}))
    rounds = [{"number": 1, "start_ms": 0, "end_ms": 1000}]  # frames 0-5
    (out / "fight.json").write_text(json.dumps({"rounds": rounds}))
    tags = [
        {"timestamp_ms": 400, "fighter": "red", "status": "confirmed"},
        {"timestamp_ms": 600, "fighter": "blue", "status": "pending"},
    ]
    (out / "tags.json").write_text(json.dumps(tags))
    return out


def probe(path: Path) -> dict[str, int]:
    result = subprocess.run(
        [
            str(FFPROBE),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-count_frames",
            "-show_entries",
            "stream=width,height,nb_read_frames,codec_name",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["streams"][0]


@pytest.mark.parametrize("ids", [False, True], ids=["corners", "ids"])
def test_render_one_round(data_dir: Path, ids: bool) -> None:
    write_fight(data_dir)
    result = overlay("fight", OverlayConfig(), round_number=1, ids=ids)
    assert result.path.name == ("overlay-ids-round-1.mp4" if ids else "overlay-round-1.mp4")
    assert result.frames == 5  # frames 0-5 of round 1, minus skipped frame 2
    assert result.tags == 1  # the pending tag is not drawn
    stream = probe(result.path)
    assert stream["codec_name"] == "h264"
    assert (stream["width"], stream["height"]) == (320, 240 + 48)
    assert int(stream["nb_read_frames"]) == 5
