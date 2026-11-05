"""The pose runner's file handling, with a fake backend (no extras needed)."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from strikelens_cv import cli
from strikelens_cv.pose import PoseConfig, model_path, pose
from strikelens_cv.pose.core import Keypoint

RED_ID = "11111111-1111-4111-8111-111111111111"


class FakeBackend:
    """Finds a pose in every box except one wider than 300 px."""

    format = "fake_2"
    landmark_names = ("head", "foot")

    def __init__(self, model: Path, config: PoseConfig) -> None:
        self.closed = False

    def estimate(self, image: Any, box: Sequence[float]) -> list[Keypoint] | None:
        assert image == "image"
        if box[2] - box[0] > 300:
            return None
        return [[box[0], box[1], 0.0, 0.9], [box[2], box[3], 0.0, 0.8]]

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "models"
    root.mkdir()
    (root / PoseConfig().model).write_bytes(b"model")
    monkeypatch.setenv("STRIKELENS_MODELS_DIR", str(root))
    return root


def write_fight(data_dir: Path, fight_json: bool = True) -> Path:
    out = data_dir / "processed" / "fight"
    out.mkdir(parents=True)
    indexes = range(4)
    (out / "frames.json").write_text(
        json.dumps({"frames": [{"index": i, "file": f"{i:06}.jpg"} for i in indexes]})
    )
    (out / "detections.json").write_text(
        json.dumps(
            {"frames": [{"index": i, "timestamp_ms": i * 200, "skipped": i == 3} for i in indexes]}
        )
    )
    red = [[10, 10, 50, 100], [10, 10, 50, 100], None, None]
    blue = [[100, 10, 140, 100], [100, 10, 500, 100], [100, 10, 140, 100], None]
    (out / "tracks.json").write_text(
        json.dumps(
            {
                "frames": [
                    {"index": i, "timestamp_ms": i * 200, "red": red[i], "blue": blue[i]}
                    for i in indexes
                ]
            }
        )
    )
    if fight_json:
        (out / "fight.json").write_text(json.dumps({"red_fighter_id": RED_ID, "segments": []}))
    return out


@pytest.mark.usefixtures("models")
def test_pose_writes_both_corners(data_dir: Path) -> None:
    out = write_fight(data_dir)
    read: list[Path] = []

    def read_image(path: Path) -> str:
        read.append(path)
        return "image"

    result = pose("fight", PoseConfig(), FakeBackend, read_image)
    assert result.out_dir == out / "keypoints"
    # Frame 3 is skipped and has no boxes, so only frames 0-2 are read.
    assert [p.name for p in read] == ["000000.jpg", "000001.jpg", "000002.jpg"]

    red = json.loads((out / "keypoints" / "red.json").read_text())
    assert red["format"] == "fake_2"
    assert red["landmarks"] == ["head", "foot"]
    assert red["keypoint_fields"] == ["x", "y", "z", "visibility"]
    assert red["corner"] == "red"
    assert red["fighter_id"] == RED_ID
    assert red["config"] == PoseConfig().as_dict()
    assert [(f["index"], f["timestamp_ms"], f["missing"]) for f in red["frames"]] == [
        (0, 0, None),
        (1, 200, None),
        (2, 400, "no_box"),
        (3, 600, "skipped"),
    ]
    assert red["frames"][0]["keypoints"] == [[10, 10, 0.0, 0.9], [50, 100, 0.0, 0.8]]

    blue = json.loads((out / "keypoints" / "blue.json").read_text())
    assert blue["fighter_id"] is None
    assert [f["missing"] for f in blue["frames"]] == [None, "no_pose", None, "skipped"]
    assert all(f["keypoints"] is None for f in blue["frames"] if f["missing"])


@pytest.mark.usefixtures("models")
def test_fighter_ids_are_null_without_fight_json(data_dir: Path) -> None:
    out = write_fight(data_dir, fight_json=False)
    pose("fight", PoseConfig(), FakeBackend, lambda _: "image")
    assert json.loads((out / "keypoints" / "red.json").read_text())["fighter_id"] is None


@pytest.mark.usefixtures("models")
def test_backend_is_closed_after_an_error(data_dir: Path) -> None:
    write_fight(data_dir)
    backends: list[FakeBackend] = []

    def factory(model: Path, config: PoseConfig) -> FakeBackend:
        backends.append(FakeBackend(model, config))
        return backends[-1]

    with pytest.raises(FileNotFoundError, match="cannot read frame"):
        pose("fight", PoseConfig(), factory, lambda _: None)
    assert backends[0].closed


@pytest.mark.usefixtures("models")
def test_pose_needs_tracking_first(data_dir: Path) -> None:
    out = write_fight(data_dir)
    (out / "tracks.json").unlink()
    with pytest.raises(FileNotFoundError, match="run strikelens-cv track first"):
        pose("fight", PoseConfig(), FakeBackend, lambda _: "image")


def test_missing_model_is_an_error_not_a_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STRIKELENS_MODELS_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="no pose model"):
        model_path(PoseConfig())


@pytest.mark.usefixtures("models")
def test_cli_reports_counts(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_fight(data_dir)
    import strikelens_cv.pose as pose_module

    def fake_pose(fight: str, config: PoseConfig) -> Any:
        return pose(fight, config, FakeBackend, lambda _: "image")

    monkeypatch.setattr(pose_module, "pose", fake_pose)
    assert cli.main(["pose", "--fight", "fight"]) == 0
    printed = capsys.readouterr().out
    assert "red: keypoints in 2 of 4 frames (no box 1, no pose 0, skipped 1)" in printed
    assert "blue: keypoints in 2 of 4 frames (no box 0, no pose 1, skipped 1)" in printed


@pytest.mark.usefixtures("data_dir", "models")
def test_cli_reports_missing_input(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["pose", "--fight", "nothing"]) == 1
    assert "run strikelens-cv ingest first" in capsys.readouterr().err
