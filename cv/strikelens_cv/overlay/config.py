"""Overlay settings, read from cv/configs/overlay.toml."""

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from strikelens_cv.paths import CONFIG_DIR

DEFAULT_OVERLAY_CONFIG = CONFIG_DIR / "overlay.toml"


@dataclass(frozen=True)
class OverlayConfig:
    min_visibility: float = 0.5
    timeline_height: int = 48
    crf: int = 20
    credit: str = "Footage: Byon Combat. Analysis: StrikeLens"

    def __post_init__(self) -> None:
        if not 0 <= self.min_visibility <= 1:
            raise ValueError("min_visibility must be between 0 and 1")
        if not 16 <= self.timeline_height <= 400:
            raise ValueError("timeline_height must be between 16 and 400 pixels")
        if not 0 <= self.crf <= 51:
            raise ValueError("crf must be between 0 and 51")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_overlay_config(path: Path = DEFAULT_OVERLAY_CONFIG) -> OverlayConfig:
    """Read a TOML config. Unknown keys are an error, so typos do not pass silently."""
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    unknown = sorted(set(raw) - set(OverlayConfig.__dataclass_fields__))
    if unknown:
        raise ValueError(f"unknown overlay settings in {path.name}: {', '.join(unknown)}")
    return OverlayConfig(**raw)
