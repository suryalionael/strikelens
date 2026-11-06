"""segments: replay suggestions from the cut list, and skipping marked segments.

Output for one fight, under data/processed/<fight>/:

- segment-suggestions.json   likely replays, for the analyst to accept or dismiss

Later stages read the analyst's segments and rounds from a saved fight (fight.json,
from the API). `frames_outside` drops replays and non-fight shots, and `in_round`
says whether a frame is inside a marked round.
"""

from strikelens_cv.segments.config import (
    DEFAULT_SEGMENT_CONFIG,
    SegmentConfig,
    load_segment_config,
)
from strikelens_cv.segments.core import (
    Round,
    Segment,
    Suggestion,
    frames_outside,
    in_round,
    in_segment,
    load_rounds,
    load_segments,
    parse_rounds,
    parse_segments,
    suggest_segments,
)
from strikelens_cv.segments.run import SUGGESTIONS_FILE, suggest, write_suggestions

__all__ = [
    "DEFAULT_SEGMENT_CONFIG",
    "SUGGESTIONS_FILE",
    "Round",
    "Segment",
    "SegmentConfig",
    "Suggestion",
    "frames_outside",
    "in_round",
    "in_segment",
    "load_rounds",
    "load_segment_config",
    "load_segments",
    "parse_rounds",
    "parse_segments",
    "suggest",
    "suggest_segments",
    "write_suggestions",
]
