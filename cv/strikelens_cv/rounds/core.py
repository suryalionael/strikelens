"""Rounds from when the broadcast scoreboard is on screen. Pure: no images here.

detect.py says, for sampled frames, whether the scoreboard is showing. This module
turns that into round suggestions the analyst accepts in the tagger.
"""

from collections.abc import Sequence
from itertools import pairwise
from typing import TypedDict

from strikelens_cv.rounds.config import RoundsConfig

Sample = tuple[int, bool]  # (timestamp_ms, scoreboard on screen)


class RoundSuggestion(TypedDict):
    number: int
    start_ms: int
    end_ms: int
    partial: bool
    reason: str


def _clock(ms: int) -> str:
    total = ms // 1000
    return f"{total // 60}:{total % 60:02}"


def visible_runs(samples: Sequence[Sample], max_gap_ms: int) -> list[tuple[int, int]]:
    """Stretches where the scoreboard shows, as (first seen, last seen) in ms.

    Gaps up to `max_gap_ms` between two sightings are bridged.
    """
    runs: list[tuple[int, int]] = []
    for t, on in sorted(samples):
        if not on:
            continue
        if runs and t - runs[-1][1] <= max_gap_ms:
            runs[-1] = (runs[-1][0], t)
        else:
            runs.append((t, t))
    return runs


def _pieces(runs: list[tuple[int, int]], config: RoundsConfig) -> list[list[tuple[int, int]]]:
    """Group stretches into rounds. A round that ends early and is followed by a
    stretch that makes up the rest of its time is one round with a pause (a
    doctor's check, a foul): the clock stops and the broadcast hides the
    scoreboard, just as it does between rounds."""
    rounds: list[list[tuple[int, int]]] = []
    for run in runs:
        if rounds:
            last = rounds[-1]
            seen = sum(b - a for a, b in last)
            short = seen < config.round_ms - config.max_hidden_tail_ms
            fits = seen + (run[1] - run[0]) <= config.round_ms + config.max_hidden_tail_ms
            if short and fits and run[0] - last[-1][1] <= config.round_ms:
                last.append(run)
                continue
        rounds.append([run])
    return rounds


def suggest_rounds(
    samples: Sequence[Sample], duration_ms: int, config: RoundsConfig
) -> list[RoundSuggestion]:
    """Round suggestions in order. A round starts when the scoreboard appears.

    It ends after `round_ms` of clock time when the scoreboard stays until close to
    that point, or later if it stays longer. Pauses inside a round (see `_pieces`)
    do not count as clock time. If the scoreboard goes away well before, the round
    is suggested as ending there and marked partial for the analyst to check: a
    stoppage, or a broadcast that hid the scoreboard before the end.
    """
    runs = [
        r for r in visible_runs(samples, config.max_gap_ms) if r[1] - r[0] >= config.min_round_ms
    ]
    groups = _pieces(runs, config)
    out: list[RoundSuggestion] = []
    for i, pieces in enumerate(groups):
        start, last_seen = pieces[0][0], pieces[-1][1]
        paused = sum(b[0] - a[1] for a, b in pairwise(pieces))
        full_end = start + config.round_ms + paused
        limit = groups[i + 1][0][0] if i + 1 < len(groups) else duration_ms
        seen = ", ".join(f"{_clock(a)}-{_clock(b)}" for a, b in pieces)
        seen = f"Scoreboard on screen {seen}"
        if paused:
            seen += f" (a pause of {_clock(paused)}: check the clock)"
        if last_seen >= full_end - config.max_hidden_tail_ms:
            end = min(max(last_seen, full_end), limit)
            partial = False
            hidden = last_seen < full_end
            reason = f"{seen}, then hidden for the last seconds." if hidden else f"{seen}."
        else:
            end = last_seen
            partial = True
            early = _clock(full_end - last_seen)
            reason = (
                f"{seen}: gone {early} before the round's full time. "
                "Check the end: a stoppage, or the scoreboard was hidden."
            )
        out.append(
            {
                "number": i + 1,
                "start_ms": start,
                "end_ms": end,
                "partial": partial,
                "reason": reason,
            }
        )
    return out
