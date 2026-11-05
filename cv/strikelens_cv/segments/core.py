"""Replay suggestions from the cut list, and skipping marked segments.

A segment is a stretch of video that is not live fight action: a replay, or a
non-fight shot such as the crowd or a corner. The analyst marks them in the
tagger and they are saved on the fight (`segments` in fight.schema.json).
`end_ms` is exclusive, as in the API's stats.
"""

import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, TypedDict, TypeVar

from strikelens_cv.ingest.cuts import Shot
from strikelens_cv.segments.config import SegmentConfig

SegmentKind = Literal["replay", "non_fight"]
KINDS: tuple[SegmentKind, ...] = ("replay", "non_fight")

Frame = TypeVar("Frame", bound=Mapping[str, Any])


class Segment(TypedDict):
    kind: SegmentKind
    start_ms: int
    end_ms: int


class Suggestion(Segment):
    reason: str


def _is_short(shot: Shot, config: SegmentConfig) -> bool:
    return shot["end_ms"] - shot["start_ms"] < config.short_shot_ms


def suggest_segments(shots: Sequence[Shot], config: SegmentConfig) -> list[Suggestion]:
    """Likely replays: runs of at least `min_run` short shots in a row.

    Live coverage holds a wide shot for a long time; a replay cuts quickly between
    angles of the same moment. This is a hint for the analyst, not a decision.
    """
    runs: list[list[Shot]] = []
    current: list[Shot] = []
    for shot in shots:
        if _is_short(shot, config):
            current.append(shot)
            continue
        if current:
            runs.append(current)
        current = []
    if current:
        runs.append(current)

    seconds = config.short_shot_ms / 1000
    return [
        {
            "kind": "replay",
            "start_ms": run[0]["start_ms"],
            "end_ms": run[-1]["end_ms"],
            "reason": f"{len(run)} shots in a row, each under {seconds:g} s",
        }
        for run in runs
        if len(run) >= config.min_run
    ]


def in_segment(timestamp_ms: int, segments: Iterable[Segment]) -> bool:
    """True when the time falls inside a segment (start inclusive, end exclusive)."""
    return any(s["start_ms"] <= timestamp_ms < s["end_ms"] for s in segments)


def frames_outside(frames: Sequence[Frame], segments: Sequence[Segment]) -> list[Frame]:
    """The frames later stages should look at: every frame not inside a segment."""
    return [f for f in frames if not in_segment(f["timestamp_ms"], segments)]


def parse_segments(fight: Mapping[str, Any]) -> list[Segment]:
    """Segments from a fight as the API returns it. A fight without them has none."""
    raw = fight.get("segments", [])
    if not isinstance(raw, list):
        raise ValueError("fight segments must be a list")
    segments: list[Segment] = []
    for item in raw:
        if not isinstance(item, dict) or item.get("kind") not in KINDS:
            raise ValueError(f"not a segment: {item!r}")
        start, end = item.get("start_ms"), item.get("end_ms")
        if not isinstance(start, int) or not isinstance(end, int) or end <= start:
            raise ValueError(f"segment times must be whole ms with end after start: {item!r}")
        segments.append({"kind": item["kind"], "start_ms": start, "end_ms": end})
    return sorted(segments, key=lambda s: s["start_ms"])


def load_segments(fight_json: Path) -> list[Segment]:
    """Read segments from a saved fight, for example data/processed/<fight>/fight.json."""
    return parse_segments(json.loads(fight_json.read_text()))
