"""Training window settings, read from cv/configs/windows.toml."""

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from strikelens_cv.paths import CONFIG_DIR

DEFAULT_WINDOWS_CONFIG = CONFIG_DIR / "windows.toml"


@dataclass(frozen=True)
class WindowsConfig:
    before_ms: int = 600
    after_ms: int = 400
    samples: int = 16
    max_missing: float = 0.25
    negatives_per_positive: float = 2
    negative_gap_ms: int = 1000
    validation_share: float = 0.2
    seed: int = 7

    def __post_init__(self) -> None:
        if self.before_ms < 0 or self.after_ms < 0 or self.before_ms + self.after_ms == 0:
            raise ValueError("before_ms and after_ms must be at least 0, and not both 0")
        if self.samples < 2:
            raise ValueError("samples must be at least 2")
        if not 0 <= self.max_missing < 1:
            raise ValueError("max_missing must be at least 0 and below 1")
        if self.negatives_per_positive < 0:
            raise ValueError("negatives_per_positive must be at least 0")
        if self.negative_gap_ms < 0:
            raise ValueError("negative_gap_ms must be at least 0")
        if not 0 <= self.validation_share < 1:
            raise ValueError("validation_share must be at least 0 and below 1")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_windows_config(path: Path = DEFAULT_WINDOWS_CONFIG) -> WindowsConfig:
    """Read a TOML config. Unknown keys are an error, so typos do not pass silently."""
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    unknown = sorted(set(raw) - set(WindowsConfig.__dataclass_fields__))
    if unknown:
        raise ValueError(f"unknown window settings in {path.name}: {', '.join(unknown)}")
    return WindowsConfig(**raw)
