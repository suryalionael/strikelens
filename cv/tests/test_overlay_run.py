"""The overlay command's checks on its inputs. Fails before OpenCV is needed."""

import json
from pathlib import Path

import pytest

from strikelens_cv.cli import main
from strikelens_cv.overlay import encoder_command


def write_inputs(data_dir: Path, skipped: bool = False) -> Path:
    out = data_dir / "processed" / "fight"
    out.mkdir(parents=True)
    frames = [{"index": i, "file": f"{i:06}.jpg", "timestamp_ms": i * 100} for i in range(5)]
    labelled = [{**f, "shot": 0, "skipped": skipped} for f in frames]
    (out / "frames.json").write_text(json.dumps({"fps": 10, "frames": frames}))
    (out / "detections.json").write_text(json.dumps({"frames": labelled, "detections": []}))
    (out / "tracks.json").write_text(json.dumps({"shots": [], "frames": []}))
    rounds = [{"number": 1, "start_ms": 0, "end_ms": 400}]
    (out / "fight.json").write_text(json.dumps({"rounds": rounds}))
    return out


class TestCli:
    def test_needs_ingest_output(self, data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["overlay", "--fight", "fight"]) == 1
        assert "run strikelens-cv ingest first" in capsys.readouterr().err

    def test_needs_tracks(self, data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        out = write_inputs(data_dir)
        (out / "tracks.json").unlink()
        assert main(["overlay", "--fight", "fight"]) == 1
        assert "run strikelens-cv track first" in capsys.readouterr().err

    def test_unknown_round(self, data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        write_inputs(data_dir)
        assert main(["overlay", "--fight", "fight", "--round", "3"]) == 1
        assert "no round 3 in fight.json" in capsys.readouterr().err

    def test_nothing_to_render(self, data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        write_inputs(data_dir, skipped=True)
        assert main(["overlay", "--fight", "fight"]) == 1
        assert "no frames to render" in capsys.readouterr().err


def test_encoder_command_writes_browser_friendly_h264(tmp_path: Path) -> None:
    command = encoder_command("ffmpeg", 640, 408, 10.0, 20, tmp_path / "o.mp4")
    assert command[command.index("-s") + 1] == "640x408"
    assert command[command.index("-r") + 1] == "10"
    assert command[command.index("-c:v") + 1] == "libx264"
    assert command[command.index("-pix_fmt", command.index("-i")) + 1] == "yuv420p"
    assert command[-1] == str(tmp_path / "o.mp4")
