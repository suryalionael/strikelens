"""Write round suggestions for one fight from its extracted frames."""

import json
from pathlib import Path
from typing import Any

from strikelens_cv import __version__
from strikelens_cv.paths import processed_dir
from strikelens_cv.rounds.config import RoundsConfig
from strikelens_cv.rounds.core import RoundSuggestion, suggest_rounds

ROUND_SUGGESTIONS_FILE = "round-suggestions.json"


def write_round_suggestions(
    out_dir: Path, frames: list[dict[str, Any]], duration_ms: int, config: RoundsConfig
) -> list[RoundSuggestion]:
    """Write round-suggestions.json next to frames.json. The tagger loads this file."""
    from strikelens_cv.rounds.detect import scoreboard_samples

    samples = scoreboard_samples(out_dir / "frames", frames, config)
    suggestions = suggest_rounds(samples, duration_ms, config)
    data = {
        "strikelens_cv": __version__,
        "config": config.as_dict(),
        "scoreboard_seconds": sum(1 for _, on in samples if on) * config.sample_ms // 1000,
        "suggestions": suggestions,
    }
    (out_dir / ROUND_SUGGESTIONS_FILE).write_text(json.dumps(data, indent=2) + "\n")
    return suggestions


def suggest_fight_rounds(fight: str, config: RoundsConfig) -> tuple[Path, list[RoundSuggestion]]:
    """Redo the round suggestions from existing frames, without running ingest again."""
    out_dir = processed_dir(fight)
    frames_json, cuts_json = out_dir / "frames.json", out_dir / "cuts.json"
    for path in (frames_json, cuts_json):
        if not path.is_file():
            raise FileNotFoundError(f"{path} not found; run strikelens-cv ingest first")
    frames = json.loads(frames_json.read_text())["frames"]
    duration_ms = json.loads(cuts_json.read_text())["duration_ms"]
    return out_dir / ROUND_SUGGESTIONS_FILE, write_round_suggestions(
        out_dir, frames, duration_ms, config
    )
