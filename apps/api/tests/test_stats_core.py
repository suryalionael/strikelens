"""Tests for pure stat functions.

The reference fixture uses figures published by Freefly Metrics (@freefly.combat)
for Nelson Julianto across 5 fights. They are a sanity check, not ground truth
from our own counting.
"""

import pytest

from app.stats.core import accuracy, attempts_by_round, strikes_per_minute

# Freefly's published figures for Nelson Julianto, 5 fights.
FREEFLY_ATTEMPTS = 608
FREEFLY_LANDED = 199
FREEFLY_SPM = 15.89
FREEFLY_R1_ATTEMPTS = 249
FREEFLY_R3_ATTEMPTS = 140


def _tag(round_: int, status: str = "confirmed") -> dict[str, object]:
    return {"round": round_, "status": status}


class TestAccuracy:
    def test_freefly_reference(self) -> None:
        result = accuracy(FREEFLY_LANDED, FREEFLY_ATTEMPTS)
        assert result is not None
        assert round(result * 100, 1) == 32.7

    def test_zero_attempts_is_undefined(self) -> None:
        assert accuracy(0, 0) is None

    def test_all_landed(self) -> None:
        assert accuracy(10, 10) == 1.0

    def test_landed_above_attempts_raises(self) -> None:
        with pytest.raises(ValueError):
            accuracy(11, 10)

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError):
            accuracy(-1, 10)


class TestStrikesPerMinute:
    def test_freefly_reference_round_trip(self) -> None:
        # Freefly did not publish total fight time. Derive the time that their
        # numbers imply and check the function reproduces their rate.
        implied_seconds = FREEFLY_ATTEMPTS / FREEFLY_SPM * 60
        result = strikes_per_minute(FREEFLY_ATTEMPTS, implied_seconds)
        assert result == pytest.approx(FREEFLY_SPM)

    def test_simple_rate(self) -> None:
        assert strikes_per_minute(30, 180) == pytest.approx(10.0)

    def test_zero_time_is_undefined(self) -> None:
        assert strikes_per_minute(5, 0) is None

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError):
            strikes_per_minute(-1, 60)


class TestAttemptsByRound:
    def test_freefly_round_split(self) -> None:
        tags = [_tag(1)] * FREEFLY_R1_ATTEMPTS + [_tag(3)] * FREEFLY_R3_ATTEMPTS
        result = attempts_by_round(tags)
        assert result[1] == FREEFLY_R1_ATTEMPTS
        assert result[3] == FREEFLY_R3_ATTEMPTS
        assert 2 not in result

    def test_ignores_pending_and_rejected(self) -> None:
        tags = [_tag(1), _tag(1, "pending"), _tag(1, "rejected"), _tag(2)]
        assert attempts_by_round(tags) == {1: 1, 2: 1}

    def test_empty(self) -> None:
        assert attempts_by_round([]) == {}
