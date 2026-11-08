"""rounds: suggest round start and end times from the broadcast scoreboard.

During a round, Byon broadcasts show a scoreboard with the clock; between rounds
it is hidden. detect.py finds when it is on screen (needs the `ingest` extra),
and core.py turns that into round suggestions (pure).

Output for one fight, under data/processed/<fight>/:

- round-suggestions.json   rounds for the analyst to check and accept in the tagger
"""

from strikelens_cv.rounds.config import DEFAULT_ROUNDS_CONFIG, RoundsConfig, load_rounds_config
from strikelens_cv.rounds.core import RoundSuggestion, suggest_rounds, visible_runs
from strikelens_cv.rounds.run import (
    ROUND_SUGGESTIONS_FILE,
    suggest_fight_rounds,
    write_round_suggestions,
)

__all__ = [
    "DEFAULT_ROUNDS_CONFIG",
    "ROUND_SUGGESTIONS_FILE",
    "RoundSuggestion",
    "RoundsConfig",
    "load_rounds_config",
    "suggest_fight_rounds",
    "suggest_rounds",
    "visible_runs",
    "write_round_suggestions",
]
