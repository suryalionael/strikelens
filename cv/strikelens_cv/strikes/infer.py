"""From strike scores over time to pending suggestions in the tag schema. Pure.

A model scores a window every `stride_ms` for each fighter. Peaks in that score
at or above the threshold, at least `min_gap_ms` apart, become CV suggestions:
tags with `source: cv`, a `confidence`, and `status: pending`, which the analyst
confirms or rejects in the tagger's review mode. `select` then keeps one
suggestion per moment and a budget per round, so review stays quicker than tagging.
"""

import uuid
from bisect import insort
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, TypedDict

# Fixed, so the same model on the same fight gives the same tag ids: posting the
# same suggestions twice is then refused as a duplicate instead of doubling them.
ID_NAMESPACE = uuid.UUID("5f8a2b52-6c1e-4c4b-9a52-6b8f4c1d2e33")


class Peak(TypedDict):
    timestamp_ms: int
    score: float
    weapon: str | None


def pick_peaks(
    times: Sequence[int],
    scores: Sequence[float],
    weapons: Sequence[str | None],
    threshold: float,
    min_gap_ms: int,
) -> list[Peak]:
    """Local maxima at or above `threshold`, highest first, keeping only those at
    least `min_gap_ms` from a higher one. Returned in time order."""
    candidates = [
        i
        for i, s in enumerate(scores)
        if s >= threshold
        and (i == 0 or s >= scores[i - 1])
        and (i == len(scores) - 1 or s >= scores[i + 1])
    ]
    kept: list[int] = []
    for i in sorted(candidates, key=lambda i: (-scores[i], times[i])):
        if all(abs(times[i] - times[j]) >= min_gap_ms for j in kept):
            kept.append(i)
    return [
        {"timestamp_ms": times[i], "score": scores[i], "weapon": weapons[i]}
        for i in sorted(kept, key=lambda i: times[i])
    ]


def round_at(rounds: Sequence[Mapping[str, Any]], ms: int) -> int | None:
    """The round a time falls in. A round's end is inclusive, as in the API's stats."""
    for r in rounds:
        if r["start_ms"] <= ms <= r["end_ms"]:
            return int(r["number"])
    return None


def in_segment(segments: Sequence[Mapping[str, Any]], ms: int) -> bool:
    return any(s["start_ms"] <= ms < s["end_ms"] for s in segments)


def suggestions(
    fight: Mapping[str, Any],
    peaks: Mapping[str, Sequence[Peak]],
    created_by: str,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Pending CV tags for a fight from each corner's peaks. Peaks outside the
    marked rounds, or inside a replay or non-fight segment, are left out."""
    created_at = (now or datetime.now(UTC)).isoformat().replace("+00:00", "Z")
    rounds = fight.get("rounds", [])
    segments = fight.get("segments", [])
    tags: list[dict[str, Any]] = []
    for corner, corner_peaks in peaks.items():
        for peak in corner_peaks:
            t = peak["timestamp_ms"]
            number = round_at(rounds, t)
            if number is None or in_segment(segments, t):
                continue
            key = f"{fight['id']}:{corner}:{t}:{created_by}"
            tags.append(
                {
                    "id": str(uuid.uuid5(ID_NAMESPACE, key)),
                    "fight_id": str(fight["id"]),
                    "round": number,
                    "timestamp_ms": t,
                    "fighter": corner,
                    "weapon": peak["weapon"],
                    "outcome": None,
                    "target": None,
                    "source": "cv",
                    "confidence": round(min(1.0, max(0.0, peak["score"])), 3),
                    "status": "pending",
                    "created_by": created_by,
                    "created_at": created_at,
                }
            )
    return sorted(tags, key=lambda tag: (tag["timestamp_ms"], tag["fighter"]))


def select(
    tags: Sequence[Mapping[str, Any]],
    max_per_round: int,
    merge_gap_ms: int,
    taken_ms: Sequence[int] = (),
    waiting: Mapping[int, int] | None = None,
) -> list[dict[str, Any]]:
    """The suggestions worth an analyst's time: one per moment, a budget per round.

    Most confident first, a suggestion is kept only if no kept suggestion, of either
    fighter, and no time in `taken_ms` (tags already in the fight) is closer than
    `merge_gap_ms`, and its round has fewer than `max_per_round`, counting the
    `waiting` suggestions already there per round. Both fighters move in an exchange,
    so one moment often scores for both: the stronger one is kept. Time order."""
    kept: list[Mapping[str, Any]] = []
    blocked = sorted(taken_ms)
    per_round: dict[int, int] = dict(waiting or {})
    for tag in sorted(tags, key=lambda t: (-(t["confidence"] or 0.0), t["timestamp_ms"])):
        t, number = tag["timestamp_ms"], tag["round"]
        if per_round.get(number, 0) >= max_per_round:
            continue
        if any(abs(t - b) < merge_gap_ms for b in blocked):
            continue
        kept.append(tag)
        insort(blocked, t)
        per_round[number] = per_round.get(number, 0) + 1
    return [dict(tag) for tag in sorted(kept, key=lambda t: (t["timestamp_ms"], t["fighter"]))]
