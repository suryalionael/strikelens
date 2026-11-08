"""Write training windows for a set of fights: files in, files out."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from strikelens_cv import __version__
from strikelens_cv.paths import data_dir, fight_slug, processed_dir
from strikelens_cv.strikes.config import WindowsConfig
from strikelens_cv.strikes.windows import Corner, Window, fight_windows, split_for, summary

TAGS_HELP = (
    "save the fight's tags from the API first: curl -s "
    "http://localhost:8000/fights/<fight-id>/tags > data/processed/<fight>/tags.json"
)


@dataclass(frozen=True)
class WindowsResult:
    out_dir: Path
    manifest: dict[str, Any]


def _read(path: Path, hint: str) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found; {hint}")
    return json.loads(path.read_text())


def windows_dir(name: str) -> Path:
    return data_dir() / "labels" / "windows" / fight_slug(name)


def build_windows(name: str, fights: list[str], config: WindowsConfig) -> WindowsResult:
    """Cut windows for every fight and write windows.jsonl and manifest.json to
    data/labels/windows/<name>/ (gitignored). All fights must share a keypoint format."""
    if not fights:
        raise ValueError("give at least one fight")
    windows: list[Window] = []
    formats: set[str] = set()
    landmarks: list[str] = []
    splits: dict[str, str] = {}
    for fight in fights:
        out_dir = processed_dir(fight)
        frames: dict[Corner, list[dict[str, Any]]] = {}
        for corner in ("red", "blue"):
            data = _read(out_dir / "keypoints" / f"{corner}.json", "run strikelens-cv pose first")
            formats.add(data["format"])
            landmarks = data["landmarks"]
            frames[corner] = sorted(data["frames"], key=lambda f: f["timestamp_ms"])
        tags = _read(out_dir / "tags.json", TAGS_HELP)
        if isinstance(tags, dict):
            tags = tags.get("tags", [])
        split = split_for(fight_slug(fight), config.validation_share)
        splits[fight_slug(fight)] = split
        windows += fight_windows(fight_slug(fight), split, frames, tags, config)
    if len(formats) > 1:
        raise ValueError(f"fights use different keypoint formats: {', '.join(sorted(formats))}")

    out = windows_dir(name)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "windows.jsonl").open("w") as handle:
        for window in windows:
            handle.write(json.dumps(window) + "\n")
    manifest = {
        "strikelens_cv": __version__,
        "format": formats.pop(),
        "landmarks": landmarks,
        "sample_fields": ["x", "y", "z", "visibility"],
        "normalised": "x, y, z relative to the fighter box: centre 0, box height 1",
        "config": config.as_dict(),
        "fights": splits,
        "counts": summary(windows),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return WindowsResult(out_dir=out, manifest=manifest)
