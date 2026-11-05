"""Tracking settings, read from cv/configs/track.toml."""

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from strikelens_cv.paths import CONFIG_DIR

DEFAULT_TRACK_CONFIG = CONFIG_DIR / "track.toml"


@dataclass(frozen=True)
class TrackConfig:
    weights: str = "yolo11n.pt"
    confidence: float = 0.4
    image_size: int = 640
    min_track_frames: int = 5
    max_feature_distance: float = 0.5

    def __post_init__(self) -> None:
        if not self.weights or "/" in self.weights or "\\" in self.weights:
            raise ValueError("weights must be a file name in models/, not a path")
        if not 0 < self.confidence < 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.image_size < 32:
            raise ValueError("image_size must be at least 32")
        if self.min_track_frames < 1:
            raise ValueError("min_track_frames must be at least 1")
        if not 0 < self.max_feature_distance <= 1:
            raise ValueError("max_feature_distance must be above 0 and at most 1")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_track_config(path: Path = DEFAULT_TRACK_CONFIG) -> TrackConfig:
    """Read a TOML config. Unknown keys are an error, so typos do not pass silently."""
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    unknown = sorted(set(raw) - set(TrackConfig.__dataclass_fields__))
    if unknown:
        raise ValueError(f"unknown track settings in {path.name}: {', '.join(unknown)}")
    return TrackConfig(**raw)
