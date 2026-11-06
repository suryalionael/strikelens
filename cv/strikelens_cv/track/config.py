"""Tracking settings, read from cv/configs/track.toml."""

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, get_args

from strikelens_cv.paths import CONFIG_DIR

DEFAULT_TRACK_CONFIG = CONFIG_DIR / "track.toml"

RefereeRule = Literal["dark", "skin"]


@dataclass(frozen=True)
class TrackConfig:
    weights: str = "yolo11n.pt"
    confidence: float = 0.4
    image_size: int = 640
    min_track_frames: int = 5
    max_feature_distance: float = 0.5
    kit_corner: bool = True
    min_kit_share: float = 0.3
    kit_min_saturation: float = 0.4
    referee_filter: bool = True
    referee_rule: RefereeRule = "dark"
    min_torso_dark: float = 0.5
    dark_max_value: int = 70
    min_torso_skin: float = 0.25
    skin_cr: tuple[int, int] = (133, 173)
    skin_cb: tuple[int, int] = (77, 127)

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
        if not 0 < self.min_kit_share <= 1:
            raise ValueError("min_kit_share must be above 0 and at most 1")
        if not 0 <= self.kit_min_saturation <= 1:
            raise ValueError("kit_min_saturation must be between 0 and 1")
        if self.referee_rule not in get_args(RefereeRule):
            raise ValueError(f"referee_rule must be one of {', '.join(get_args(RefereeRule))}")
        if not 0 <= self.min_torso_dark <= 1:
            raise ValueError("min_torso_dark must be between 0 and 1")
        if not 0 <= self.dark_max_value <= 255:
            raise ValueError("dark_max_value must be between 0 and 255")
        if not 0 <= self.min_torso_skin <= 1:
            raise ValueError("min_torso_skin must be between 0 and 1")
        for name in ("skin_cr", "skin_cb"):
            low, high = getattr(self, name)
            if not 0 <= low < high <= 255:
                raise ValueError(f"{name} must be [low, high] with 0 <= low < high <= 255")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_track_config(path: Path = DEFAULT_TRACK_CONFIG) -> TrackConfig:
    """Read a TOML config. Unknown keys are an error, so typos do not pass silently."""
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    unknown = sorted(set(raw) - set(TrackConfig.__dataclass_fields__))
    if unknown:
        raise ValueError(f"unknown track settings in {path.name}: {', '.join(unknown)}")
    # TOML has arrays, not tuples. Anything that is not a pair fails validation.
    for name in ("skin_cr", "skin_cb"):
        if name in raw:
            if not isinstance(raw[name], list) or len(raw[name]) != 2:
                raise ValueError(f"{name} must be a pair, for example [133, 173]")
            raw[name] = tuple(raw[name])
    return TrackConfig(**raw)
