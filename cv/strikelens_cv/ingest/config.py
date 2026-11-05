"""Ingest settings, read from cv/configs/ingest.toml."""

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from strikelens_cv.paths import CONFIG_DIR

DEFAULT_CONFIG = CONFIG_DIR / "ingest.toml"


@dataclass(frozen=True)
class IngestConfig:
    fps: float = 10
    jpeg_quality: int = 3
    cut_threshold: float = 27.0
    min_shot_ms: int = 400

    def __post_init__(self) -> None:
        if not 0 < self.fps <= 120:
            raise ValueError("fps must be above 0 and at most 120")
        if not 2 <= self.jpeg_quality <= 31:
            raise ValueError("jpeg_quality must be between 2 and 31")
        if self.cut_threshold <= 0:
            raise ValueError("cut_threshold must be above 0")
        if self.min_shot_ms < 0:
            raise ValueError("min_shot_ms must not be negative")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(path: Path = DEFAULT_CONFIG) -> IngestConfig:
    """Read a TOML config. Unknown keys are an error, so typos do not pass silently."""
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    known = set(IngestConfig.__dataclass_fields__)
    unknown = sorted(set(raw) - known)
    if unknown:
        raise ValueError(f"unknown ingest settings in {path.name}: {', '.join(unknown)}")
    return IngestConfig(**raw)
