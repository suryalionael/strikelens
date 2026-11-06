"""Write replay suggestions for one fight from its cut list."""

import json
from pathlib import Path
from typing import TYPE_CHECKING

from strikelens_cv import __version__
from strikelens_cv.paths import processed_dir
from strikelens_cv.segments.config import SegmentConfig
from strikelens_cv.segments.core import Suggestion, suggest_segments

if TYPE_CHECKING:
    # Only a type here; see segments/core.py.
    from strikelens_cv.ingest.cuts import Shot

SUGGESTIONS_FILE = "segment-suggestions.json"


def write_suggestions(
    out_dir: Path, shots: list["Shot"], config: SegmentConfig
) -> list[Suggestion]:
    """Write segment-suggestions.json next to cuts.json. The tagger loads this file."""
    suggestions = suggest_segments(shots, config)
    data = {"strikelens_cv": __version__, "config": config.as_dict(), "suggestions": suggestions}
    (out_dir / SUGGESTIONS_FILE).write_text(json.dumps(data, indent=2) + "\n")
    return suggestions


def suggest(fight: str, config: SegmentConfig) -> tuple[Path, list[Suggestion]]:
    """Redo the suggestions from an existing cuts.json, without running ingest again."""
    out_dir = processed_dir(fight)
    cuts = out_dir / "cuts.json"
    if not cuts.is_file():
        raise FileNotFoundError(f"no cut list at {cuts}; run strikelens-cv ingest first")
    shots: list[Shot] = json.loads(cuts.read_text())["shots"]
    return out_dir / SUGGESTIONS_FILE, write_suggestions(out_dir, shots, config)
