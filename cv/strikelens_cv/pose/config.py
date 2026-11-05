"""Pose settings, read from cv/configs/pose.toml."""

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from strikelens_cv.paths import CONFIG_DIR

DEFAULT_POSE_CONFIG = CONFIG_DIR / "pose.toml"

BACKENDS = ("mediapipe",)


@dataclass(frozen=True)
class PoseConfig:
    backend: str = "mediapipe"
    model: str = "pose_landmarker_full.task"
    box_margin: float = 0.1
    min_pose_confidence: float = 0.5

    def __post_init__(self) -> None:
        if self.backend not in BACKENDS:
            raise ValueError(f"backend must be one of: {', '.join(BACKENDS)}")
        if not self.model or "/" in self.model or "\\" in self.model:
            raise ValueError("model must be a file name in models/, not a path")
        if not 0 <= self.box_margin <= 1:
            raise ValueError("box_margin must be between 0 and 1")
        if not 0 < self.min_pose_confidence < 1:
            raise ValueError("min_pose_confidence must be between 0 and 1")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_pose_config(path: Path = DEFAULT_POSE_CONFIG) -> PoseConfig:
    """Read a TOML config. Unknown keys are an error, so typos do not pass silently."""
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    unknown = sorted(set(raw) - set(PoseConfig.__dataclass_fields__))
    if unknown:
        raise ValueError(f"unknown pose settings in {path.name}: {', '.join(unknown)}")
    return PoseConfig(**raw)
