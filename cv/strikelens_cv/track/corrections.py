"""Manual track corrections: which track is red, blue, or neither.

The format is meant for the tagger to write later, when an analyst fixes a swap:

    {"corrections": [{"shot": 3, "track_id": 12, "corner": "red"}]}

`corner` is "red", "blue", or "none". "none" removes the track, for example the
referee. Shot and track IDs are the ones in detections.json.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, TypedDict

Corner = Literal["red", "blue"]
CorrectionCorner = Literal["red", "blue", "none"]
CORRECTION_CORNERS: tuple[CorrectionCorner, ...] = ("red", "blue", "none")

# (shot, track_id) -> corner
Corrections = dict[tuple[int, int], CorrectionCorner]


class Correction(TypedDict):
    shot: int
    track_id: int
    corner: CorrectionCorner


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def parse_corrections(data: Mapping[str, Any]) -> Corrections:
    """Validate a corrections file. A track corrected twice keeps the last entry."""
    raw = data.get("corrections")
    if not isinstance(raw, list):
        raise ValueError('corrections file needs a "corrections" list')
    out: Corrections = {}
    for number, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"correction {number} is not an object")
        shot, track_id, corner = item.get("shot"), item.get("track_id"), item.get("corner")
        if not _whole(shot) or not _whole(track_id):
            raise ValueError(f"correction {number} needs whole-number shot and track_id")
        if corner not in CORRECTION_CORNERS:
            raise ValueError(f"correction {number}: corner must be red, blue, or none")
        out[(shot, track_id)] = corner
    return out


def load_corrections(path: Path) -> Corrections:
    return parse_corrections(json.loads(path.read_text()))
