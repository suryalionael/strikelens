"""Round suggestion settings, read from cv/configs/rounds.toml."""

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from strikelens_cv.paths import CONFIG_DIR

DEFAULT_ROUNDS_CONFIG = CONFIG_DIR / "rounds.toml"


@dataclass(frozen=True)
class RoundsConfig:
    scoreboard_region: tuple[float, float, float, float] = (0.02, 0.62, 0.45, 0.97)
    grid: tuple[int, int] = (6, 4)
    match: float = 0.9
    sample_ms: int = 1000
    round_ms: int = 180_000
    max_gap_ms: int = 15_000
    min_round_ms: int = 20_000
    max_hidden_tail_ms: int = 20_000

    def __post_init__(self) -> None:
        x1, y1, x2, y2 = self.scoreboard_region
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise ValueError("scoreboard_region must be [left, top, right, bottom] inside 0-1")
        if min(self.grid) < 1:
            raise ValueError("grid must be at least [1, 1]")
        if not 0 < self.match < 1:
            raise ValueError("match must be between 0 and 1")
        for name in ("sample_ms", "round_ms", "min_round_ms"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be above 0")
        for name in ("max_gap_ms", "max_hidden_tail_ms"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be at least 0")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_rounds_config(path: Path = DEFAULT_ROUNDS_CONFIG) -> RoundsConfig:
    """Read a TOML config. Unknown keys are an error, so typos do not pass silently."""
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    unknown = sorted(set(raw) - set(RoundsConfig.__dataclass_fields__))
    if unknown:
        raise ValueError(f"unknown round settings in {path.name}: {', '.join(unknown)}")
    for name, size in (("scoreboard_region", 4), ("grid", 2)):
        if name in raw:
            if not isinstance(raw[name], list) or len(raw[name]) != size:
                raise ValueError(f"{name} must be a list of {size} numbers")
            raw[name] = tuple(raw[name])
    return RoundsConfig(**raw)
