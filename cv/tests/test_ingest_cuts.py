import builtins
from pathlib import Path
from typing import Any

import pytest

from strikelens_cv.ingest import cuts
from strikelens_cv.ingest.config import IngestConfig


def test_no_cuts_means_one_shot_for_the_whole_video() -> None:
    assert cuts.shots_from_scenes([], duration_ms=60_000, min_shot_ms=400) == [
        {"index": 0, "start_ms": 0, "end_ms": 60_000}
    ]


def test_scenes_become_shots_in_ms() -> None:
    shots = cuts.shots_from_scenes([(0, 2.0), (2.0, 5.5)], duration_ms=5_500, min_shot_ms=400)
    assert shots == [
        {"index": 0, "start_ms": 0, "end_ms": 2_000},
        {"index": 1, "start_ms": 2_000, "end_ms": 5_500},
    ]
    assert cuts.cut_times_ms(shots) == [2_000]


def test_a_flash_is_merged_into_the_shot_before() -> None:
    shots = cuts.shots_from_scenes(
        [(0, 3.0), (3.0, 3.1), (3.1, 8.0)], duration_ms=8_000, min_shot_ms=400
    )
    # 3.0-3.1 is too short to be a shot; it joins 0-3.0, and 3.1 stays a cut.
    assert shots == [
        {"index": 0, "start_ms": 0, "end_ms": 3_100},
        {"index": 1, "start_ms": 3_100, "end_ms": 8_000},
    ]


def test_a_short_first_shot_is_merged_into_the_next() -> None:
    shots = cuts.shots_from_scenes([(0, 0.2), (0.2, 4.0)], duration_ms=4_000, min_shot_ms=400)
    assert shots == [{"index": 0, "start_ms": 0, "end_ms": 4_000}]


def test_min_shot_zero_keeps_every_scene() -> None:
    scenes = [(0, 1.0), (1.0, 1.05), (1.05, 2.0)]
    assert len(cuts.shots_from_scenes(scenes, duration_ms=2_000, min_shot_ms=0)) == 3


def test_missing_extra_gives_install_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def no_scenedetect(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "scenedetect":
            raise ImportError("No module named 'scenedetect'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_scenedetect)
    with pytest.raises(RuntimeError, match="uv sync --extra ingest"):
        cuts.detect_scenes(Path("fight.mp4"), IngestConfig())
