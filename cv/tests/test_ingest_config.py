from pathlib import Path

import pytest

from strikelens_cv.ingest.config import DEFAULT_CONFIG, IngestConfig, load_config


def test_committed_config_loads() -> None:
    config = load_config(DEFAULT_CONFIG)
    assert config == IngestConfig(fps=10, jpeg_quality=3, cut_threshold=27.0, min_shot_ms=400)


def test_missing_keys_use_defaults(tmp_path: Path) -> None:
    path = tmp_path / "ingest.toml"
    path.write_text("fps = 25\n")
    assert load_config(path) == IngestConfig(fps=25)


def test_unknown_keys_are_an_error(tmp_path: Path) -> None:
    path = tmp_path / "ingest.toml"
    path.write_text("fps = 10\nfsp = 5\n")
    with pytest.raises(ValueError, match=r"unknown ingest settings in ingest\.toml: fsp"):
        load_config(path)


@pytest.mark.parametrize(
    "changes",
    [
        {"fps": 0},
        {"fps": 500},
        {"jpeg_quality": 1},
        {"jpeg_quality": 40},
        {"cut_threshold": 0},
        {"min_shot_ms": -1},
    ],
)
def test_invalid_values_are_rejected(changes: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        IngestConfig(**changes)  # type: ignore[arg-type]
