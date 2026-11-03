"""Pure stat functions.

Every function here takes plain values and returns plain values. No database,
no HTTP, no UI. Formulas and edge cases are documented in
docs/stat-definitions.md.
"""

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any


def accuracy(landed: int, attempts: int) -> float | None:
    """Share of attempts that landed, from 0.0 to 1.0.

    Returns None when there are no attempts: accuracy is undefined, not zero.
    """
    if landed < 0 or attempts < 0:
        raise ValueError("landed and attempts must be non-negative")
    if landed > attempts:
        raise ValueError("landed cannot exceed attempts")
    if attempts == 0:
        return None
    return landed / attempts


def strikes_per_minute(attempts: int, fight_time_seconds: float) -> float | None:
    """Strike attempts per minute of fight time.

    Returns None when fight time is zero: the rate is undefined.
    """
    if attempts < 0 or fight_time_seconds < 0:
        raise ValueError("attempts and fight_time_seconds must be non-negative")
    if fight_time_seconds == 0:
        return None
    return attempts / (fight_time_seconds / 60)


def attempts_by_round(tags: Iterable[Mapping[str, Any]]) -> dict[int, int]:
    """Count confirmed strike attempts per round.

    Only tags with status "confirmed" count. Pending and rejected tags are ignored.
    Rounds with no confirmed tags are absent from the result.
    """
    counts = Counter(tag["round"] for tag in tags if tag["status"] == "confirmed")
    return dict(sorted(counts.items()))
