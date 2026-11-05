"""segments: replay suggestions from the cut list, and skipping marked segments.

Output for one fight, under data/processed/<fight>/:

- segment-suggestions.json   likely replays, for the analyst to accept or dismiss

Later stages read the analyst's segments from a saved fight (fight.json, from the
API) and use `frames_outside` so they never process replays or non-fight shots.
"""

from strikelens_cv.segments.config import (
    DEFAULT_SEGMENT_CONFIG,
    SegmentConfig,
    load_segment_config,
)
from strikelens_cv.segments.core import (
    Segment,
    Suggestion,
    frames_outside,
    in_segment,
    load_segments,
    parse_segments,
    suggest_segments,
)
from strikelens_cv.segments.run import SUGGESTIONS_FILE, suggest, write_suggestions

__all__ = [
    "DEFAULT_SEGMENT_CONFIG",
    "SUGGESTIONS_FILE",
    "Segment",
    "SegmentConfig",
    "Suggestion",
    "frames_outside",
    "in_segment",
    "load_segment_config",
    "load_segments",
    "parse_segments",
    "suggest",
    "suggest_segments",
    "write_suggestions",
]
