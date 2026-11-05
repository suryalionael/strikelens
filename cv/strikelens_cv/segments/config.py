"""Replay suggestion settings, read from cv/configs/segments.toml."""

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from strikelens_cv.paths import CONFIG_DIR

DEFAULT_SEGMENT_CONFIG = CONFIG_DIR / "segments.toml"


@dataclass(frozen=True)
class SegmentConfig:
    short_shot_ms: int = 2500
    min_run: int = 3

    def __post_init__(self) -> None:
        if self.short_shot_ms <= 0:
            raise ValueError("short_shot_ms must be above 0")
        if self.min_run < 1:
            raise ValueError("min_run must be at least 1")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_segment_config(path: Path = DEFAULT_SEGMENT_CONFIG) -> SegmentConfig:
    """Read a TOML config. Unknown keys are an error, so typos do not pass silently."""
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    unknown = sorted(set(raw) - set(SegmentConfig.__dataclass_fields__))
    if unknown:
        raise ValueError(f"unknown segment settings in {path.name}: {', '.join(unknown)}")
    return SegmentConfig(**raw)
