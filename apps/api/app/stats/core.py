"""Pure stat functions.

Every function here takes plain values and returns plain values. No database,
no HTTP, no UI. Formulas and edge cases are documented in
docs/stat-definitions.md. Where that page calls a rule provisional, the code
follows the provisional rule and says so in a comment.
"""

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, Literal, TypedDict

Corner = Literal["red", "blue"]
CORNERS: tuple[Corner, ...] = ("red", "blue")

# Groups from docs/tag-schema.md#weapons.
WEAPON_GROUPS: dict[str, str] = {
    "jab": "punch",
    "cross": "punch",
    "hook": "punch",
    "uppercut": "punch",
    "kick": "kick",
    "teep": "kick",
    "knee": "knee",
    "elbow": "elbow",
}
WEAPONS: tuple[str, ...] = tuple(WEAPON_GROUPS)
GROUPS: tuple[str, ...] = ("punch", "kick", "knee", "elbow")
TARGETS: tuple[str, ...] = ("head", "body", "legs")

# Rules the stats follow until Freefly confirms them (docs/stat-definitions.md).
# The stat cards show these so nobody mistakes a provisional number for a final one.
PROVISIONAL_RULES: tuple[str, ...] = (
    "Every strike in a combination is its own attempt.",
    "Strikes on the guard and checked kicks count as blocked, not landed.",
    "Strikes per minute uses attempts, not landed strikes.",
    "Pauses inside a round count as fight time.",
    "Target distribution is based on landed strikes; the attempts version is also shown.",
    "When fewer rounds are marked than scheduled, the last marked round is partial.",
)

Tag = Mapping[str, Any]
Round = Mapping[str, Any]


class Split(TypedDict):
    attempts: int
    landed: int
    accuracy: float | None
    strikes_per_minute: float | None


class RoundSplit(Split):
    round: int


class MixEntry(TypedDict):
    attempts: int
    landed: int
    share: float | None


class TargetEntry(TypedDict):
    count: int
    share: float | None


class FighterStats(TypedDict):
    totals: Split
    by_round: list[RoundSplit]
    weapons: dict[str, MixEntry]
    weapon_groups: dict[str, MixEntry]
    targets_landed: dict[str, TargetEntry]
    targets_attempted: dict[str, TargetEntry]


class RoundInfo(TypedDict):
    number: int
    start_ms: int
    end_ms: int
    time_s: float
    partial: bool


class FightStats(TypedDict):
    fight_time_s: float
    rounds: list[RoundInfo]
    fighters: dict[Corner, FighterStats]
    uncounted_tags: int


# Basic ratios


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

    Provisional: uses attempts, not landed (open question 6).
    Returns None when fight time is zero: the rate is undefined.
    """
    if attempts < 0 or fight_time_seconds < 0:
        raise ValueError("attempts and fight_time_seconds must be non-negative")
    if fight_time_seconds == 0:
        return None
    return attempts / (fight_time_seconds / 60)


def share(part: int, whole: int) -> float | None:
    """part / whole, or None when whole is zero."""
    if part < 0 or whole < 0:
        raise ValueError("part and whole must be non-negative")
    if part > whole:
        raise ValueError("part cannot exceed whole")
    return None if whole == 0 else part / whole


# Time


def round_time_s(round_: Round) -> float:
    """Seconds between the round's start and end marks."""
    return (round_["end_ms"] - round_["start_ms"]) / 1000


def fight_time_s(rounds: Iterable[Round]) -> float:
    """Sum of round times. Provisional: pauses inside a round are included."""
    return sum(round_time_s(r) for r in rounds)


def partial_rounds(rounds: Sequence[Round], scheduled_rounds: int) -> set[int]:
    """Round numbers cut short by a stoppage.

    Provisional detection: when fewer rounds are marked than scheduled, the last
    marked round counts as partial. While rounds are still being marked, the latest
    round is flagged too.
    """
    if not rounds or len(rounds) >= scheduled_rounds:
        return set()
    return {max(r["number"] for r in rounds)}


# Tag filters


def attempts_by_round(tags: Iterable[Tag]) -> dict[int, int]:
    """Count confirmed strike attempts per round.

    Only tags with status "confirmed" count. Pending and rejected tags are ignored.
    Rounds with no confirmed tags are absent from the result.
    """
    counts = Counter(tag["round"] for tag in tags if tag["status"] == "confirmed")
    return dict(sorted(counts.items()))


def in_marked_round(tag: Tag, rounds: Iterable[Round]) -> bool:
    """True when the tag's round is marked and its time falls inside that round."""
    return any(
        r["number"] == tag["round"] and r["start_ms"] <= tag["timestamp_ms"] <= r["end_ms"]
        for r in rounds
    )


def counted_tags(tags: Iterable[Tag], rounds: Sequence[Round]) -> list[Tag]:
    """Tags that count towards stats: confirmed, and inside their marked round.

    Source does not matter. A confirmed CV suggestion counts like a human tag.
    """
    return [t for t in tags if t["status"] == "confirmed" and in_marked_round(t, rounds)]


# Splits and distributions


def split(tags: Sequence[Tag], time_s: float) -> Split:
    """Attempts, landed, accuracy, and strikes per minute for one fighter's tags.

    Provisional: every tag is one attempt, and only outcome "landed" lands
    (open questions 1 and 2).
    """
    attempts = len(tags)
    landed = sum(1 for t in tags if t["outcome"] == "landed")
    return {
        "attempts": attempts,
        "landed": landed,
        "accuracy": accuracy(landed, attempts),
        "strikes_per_minute": strikes_per_minute(attempts, time_s),
    }


def weapon_mix(tags: Sequence[Tag]) -> dict[str, MixEntry]:
    """Per weapon: attempts, landed, and share of all attempts."""
    return _mix(tags, WEAPONS, lambda t: t["weapon"])


def weapon_group_mix(tags: Sequence[Tag]) -> dict[str, MixEntry]:
    """Per group (punch, kick, knee, elbow): attempts, landed, and share of attempts."""
    return _mix(tags, GROUPS, lambda t: WEAPON_GROUPS.get(t["weapon"]))


def _mix(
    tags: Sequence[Tag], keys: Sequence[str], key_of: Callable[[Tag], str | None]
) -> dict[str, MixEntry]:
    attempts = Counter(key_of(t) for t in tags)
    landed = Counter(key_of(t) for t in tags if t["outcome"] == "landed")
    return {
        k: {"attempts": attempts[k], "landed": landed[k], "share": share(attempts[k], len(tags))}
        for k in keys
    }


def target_distribution(
    tags: Sequence[Tag], basis: Literal["landed", "attempts"]
) -> dict[str, TargetEntry]:
    """Share of strikes per target.

    Provisional: the headline version uses landed strikes, because for a missed
    strike the target is a guess at intent. The attempts version is kept too
    (open question 8).
    """
    pool = [t for t in tags if t["outcome"] == "landed"] if basis == "landed" else list(tags)
    counts = Counter(t["target"] for t in pool)
    return {k: {"count": counts[k], "share": share(counts[k], len(pool))} for k in TARGETS}


# Whole fight


def fighter_stats(tags: Sequence[Tag], rounds: Sequence[Round]) -> FighterStats:
    """Every v1 stat for one fighter. `tags` must already be counted and filtered."""
    by_round: list[RoundSplit] = []
    for r in sorted(rounds, key=lambda r: r["number"]):
        in_round = [t for t in tags if t["round"] == r["number"]]
        by_round.append({"round": r["number"], **split(in_round, round_time_s(r))})
    return {
        "totals": split(tags, fight_time_s(rounds)),
        "by_round": by_round,
        "weapons": weapon_mix(tags),
        "weapon_groups": weapon_group_mix(tags),
        "targets_landed": target_distribution(tags, "landed"),
        "targets_attempted": target_distribution(tags, "attempts"),
    }


def fight_stats(tags: Iterable[Tag], rounds: Sequence[Round], scheduled_rounds: int) -> FightStats:
    """Every v1 stat for both fighters in one fight.

    `uncounted_tags` is how many confirmed tags fall outside every marked round,
    for example after the bell, so the tagger can warn about them.
    """
    all_tags = list(tags)
    counted = counted_tags(all_tags, rounds)
    confirmed = sum(1 for t in all_tags if t["status"] == "confirmed")
    partial = partial_rounds(rounds, scheduled_rounds)
    return {
        "fight_time_s": fight_time_s(rounds),
        "rounds": [
            {
                "number": r["number"],
                "start_ms": r["start_ms"],
                "end_ms": r["end_ms"],
                "time_s": round_time_s(r),
                "partial": r["number"] in partial,
            }
            for r in sorted(rounds, key=lambda r: r["number"])
        ],
        "fighters": {
            corner: fighter_stats([t for t in counted if t["fighter"] == corner], rounds)
            for corner in CORNERS
        },
        "uncounted_tags": confirmed - len(counted),
    }
