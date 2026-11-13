"""Tests for the whole-fight stat functions in app/stats/core.py.

Edge cases follow docs/stat-definitions.md. Numbers are made up for the tests.
"""

from typing import Any

import pytest

from app.stats.core import (
    counted_tags,
    fight_stats,
    fight_time_s,
    in_marked_round,
    in_segment,
    partial_rounds,
    round_time_s,
    share,
    split,
    target_distribution,
    weapon_group_mix,
    weapon_mix,
)

ROUNDS: list[dict[str, int]] = [
    {"number": 1, "start_ms": 0, "end_ms": 180_000},
    {"number": 2, "start_ms": 240_000, "end_ms": 420_000},
]


def tag(
    *,
    fighter: str = "red",
    round_: int = 1,
    ms: int = 10_000,
    weapon: str = "jab",
    outcome: str = "landed",
    target: str | None = "head",
    status: str = "confirmed",
    source: str = "human",
) -> dict[str, Any]:
    return {
        "fighter": fighter,
        "round": round_,
        "timestamp_ms": ms,
        "weapon": weapon,
        "outcome": outcome,
        "target": target,
        "status": status,
        "source": source,
    }


class TestTime:
    def test_round_time_is_between_the_marks(self) -> None:
        assert round_time_s({"start_ms": 1_000, "end_ms": 181_500}) == 180.5

    def test_fight_time_sums_rounds_and_skips_breaks(self) -> None:
        assert fight_time_s(ROUNDS) == 360.0

    def test_no_rounds_is_zero_time(self) -> None:
        assert fight_time_s([]) == 0


class TestPartialRounds:
    def test_full_distance_has_no_partial_round(self) -> None:
        assert partial_rounds(ROUNDS, scheduled_rounds=2) == set()

    def test_stoppage_marks_the_last_round(self) -> None:
        assert partial_rounds(ROUNDS, scheduled_rounds=3) == {2}

    def test_no_rounds_marked(self) -> None:
        assert partial_rounds([], scheduled_rounds=3) == set()


class TestCountedTags:
    def test_only_confirmed_tags_count(self) -> None:
        tags = [tag(), tag(status="pending"), tag(status="rejected")]
        assert len(counted_tags(tags, ROUNDS)) == 1

    def test_confirmed_cv_counts_like_human(self) -> None:
        assert len(counted_tags([tag(source="cv"), tag()], ROUNDS)) == 2

    def test_tag_between_rounds_does_not_count(self) -> None:
        assert counted_tags([tag(round_=1, ms=200_000)], ROUNDS) == []

    def test_tag_in_an_unmarked_round_does_not_count(self) -> None:
        assert counted_tags([tag(round_=3, ms=500_000)], ROUNDS) == []

    def test_round_marks_are_inclusive(self) -> None:
        assert in_marked_round(tag(ms=0), ROUNDS)
        assert in_marked_round(tag(ms=180_000), ROUNDS)

    def test_round_field_must_match_the_time(self) -> None:
        # Time is in round 2, but the tag says round 1, for example after a mark moved.
        assert not in_marked_round(tag(round_=1, ms=300_000), ROUNDS)


class TestSplit:
    def test_counts_and_rates(self) -> None:
        tags = [tag(), tag(outcome="missed"), tag(outcome="blocked"), tag()]
        assert split(tags, 120) == {
            "attempts": 4,
            "landed": 2,
            "accuracy": 0.5,
            "strikes_per_minute": 2.0,
        }

    def test_blocked_lowers_accuracy(self) -> None:
        result = split([tag(), tag(outcome="blocked")], 60)
        assert result["accuracy"] == 0.5

    def test_no_tags_gives_undefined_accuracy_not_zero(self) -> None:
        result = split([], 180)
        assert result["attempts"] == 0
        assert result["accuracy"] is None
        assert result["strikes_per_minute"] == 0.0

    def test_zero_time_gives_undefined_rate(self) -> None:
        assert split([tag()], 0)["strikes_per_minute"] is None


class TestShare:
    def test_share(self) -> None:
        assert share(1, 4) == 0.25

    def test_zero_whole_is_undefined(self) -> None:
        assert share(0, 0) is None

    def test_invalid_inputs_raise(self) -> None:
        with pytest.raises(ValueError):
            share(5, 4)
        with pytest.raises(ValueError):
            share(-1, 4)


class TestWeaponMix:
    def test_per_weapon_on_attempts_with_landed(self) -> None:
        tags = [tag(weapon="jab"), tag(weapon="jab", outcome="missed"), tag(weapon="kick")]
        mix = weapon_mix(tags)
        assert mix["jab"] == {"attempts": 2, "landed": 1, "share": 2 / 3}
        assert mix["kick"] == {"attempts": 1, "landed": 1, "share": 1 / 3}
        assert mix["elbow"] == {"attempts": 0, "landed": 0, "share": 0.0}
        assert set(mix) == {"jab", "cross", "hook", "uppercut", "kick", "teep", "knee", "elbow"}

    def test_groups_roll_up_weapons(self) -> None:
        tags = [tag(weapon="jab"), tag(weapon="hook"), tag(weapon="teep"), tag(weapon="kick")]
        groups = weapon_group_mix(tags)
        assert groups["punch"]["attempts"] == 2
        assert groups["kick"]["attempts"] == 2
        assert groups["kick"]["share"] == 0.5
        assert set(groups) == {"punch", "kick", "knee", "elbow"}

    def test_zero_attempts_is_undefined_for_every_weapon(self) -> None:
        assert all(entry["share"] is None for entry in weapon_mix([]).values())
        assert all(entry["share"] is None for entry in weapon_group_mix([]).values())


class TestTargetDistribution:
    TAGS = (
        tag(target="head"),
        tag(target="body"),
        tag(target="body"),
        tag(target="legs", outcome="missed"),
    )

    def test_landed_basis_ignores_misses(self) -> None:
        dist = target_distribution(list(self.TAGS), "landed")
        assert dist["head"] == {"count": 1, "share": 1 / 3}
        assert dist["body"] == {"count": 2, "share": 2 / 3}
        assert dist["legs"] == {"count": 0, "share": 0.0}

    def test_attempts_basis_counts_everything(self) -> None:
        dist = target_distribution(list(self.TAGS), "attempts")
        assert dist["legs"] == {"count": 1, "share": 0.25}

    def test_tags_without_a_target_are_left_out_of_the_shares(self) -> None:
        tags = [tag(target="head"), tag(target="body"), tag(target=None), tag(target=None)]
        dist = target_distribution(tags, "landed")
        assert dist["head"] == {"count": 1, "share": 0.5}
        assert dist["body"] == {"count": 1, "share": 0.5}

    def test_no_targets_set_is_undefined(self) -> None:
        dist = target_distribution([tag(target=None)], "landed")
        assert all(entry == {"count": 0, "share": None} for entry in dist.values())

    def test_zero_landed_is_undefined(self) -> None:
        dist = target_distribution([tag(outcome="missed")], "landed")
        assert all(entry["share"] is None for entry in dist.values())


REPLAY = {"kind": "replay", "start_ms": 60_000, "end_ms": 70_000}
CROWD = {"kind": "non_fight", "start_ms": 100_000, "end_ms": 110_000}


class TestSegments:
    def test_start_is_inside_and_end_is_not(self) -> None:
        assert in_segment(tag(ms=60_000), [REPLAY])
        assert in_segment(tag(ms=69_999), [REPLAY])
        assert not in_segment(tag(ms=70_000), [REPLAY])
        assert not in_segment(tag(ms=59_999), [REPLAY])

    def test_no_segments(self) -> None:
        assert not in_segment(tag(), [])

    def test_tags_inside_any_segment_do_not_count(self) -> None:
        tags = [tag(ms=65_000), tag(ms=105_000), tag(ms=80_000)]
        assert counted_tags(tags, ROUNDS, [REPLAY, CROWD]) == [tags[2]]

    def test_segments_are_optional(self) -> None:
        assert counted_tags([tag(ms=65_000)], ROUNDS) == [tag(ms=65_000)]

    def test_fight_stats_reports_segment_tags_separately(self) -> None:
        tags = [
            tag(ms=65_000),  # in the replay
            tag(ms=105_000, status="pending"),  # pending, ignored everywhere
            tag(ms=200_000),  # between rounds, but in the crowd shot
            tag(ms=205_000, round_=2),  # between rounds, outside every segment
            tag(ms=10_000),  # counted
        ]
        crowd_between_rounds = {"kind": "non_fight", "start_ms": 200_000, "end_ms": 201_000}
        stats = fight_stats(tags, ROUNDS, 2, [REPLAY, crowd_between_rounds])
        assert stats["segment_tags"] == 2
        assert stats["uncounted_tags"] == 1
        assert stats["fighters"]["red"]["totals"]["attempts"] == 1

    def test_segments_do_not_shorten_round_time(self) -> None:
        stats = fight_stats([], ROUNDS, 2, [REPLAY, CROWD])
        assert stats["fight_time_s"] == 360.0
        assert stats["rounds"][0]["time_s"] == 180.0


class TestFightStats:
    def test_whole_fight(self) -> None:
        tags = [
            tag(fighter="red", round_=1, ms=10_000, weapon="kick", target="body"),
            tag(fighter="red", round_=1, ms=20_000, weapon="jab", outcome="missed"),
            tag(fighter="red", round_=2, ms=300_000, weapon="cross"),
            tag(fighter="blue", round_=2, ms=310_000, weapon="teep", outcome="blocked"),
            tag(fighter="blue", round_=2, ms=320_000, status="pending"),
            tag(fighter="red", round_=1, ms=200_000),  # between rounds
        ]
        stats = fight_stats(tags, ROUNDS, scheduled_rounds=3)

        assert stats["fight_time_s"] == 360.0
        assert stats["uncounted_tags"] == 1
        assert [r["partial"] for r in stats["rounds"]] == [False, True]
        assert stats["rounds"][1]["time_s"] == 180.0

        red = stats["fighters"]["red"]
        assert red["totals"] == {
            "attempts": 3,
            "landed": 2,
            "accuracy": 2 / 3,
            "strikes_per_minute": 0.5,
        }
        assert red["by_round"] == [
            {"round": 1, "attempts": 2, "landed": 1, "accuracy": 0.5, "strikes_per_minute": 2 / 3},
            {"round": 2, "attempts": 1, "landed": 1, "accuracy": 1.0, "strikes_per_minute": 1 / 3},
        ]
        assert red["weapon_groups"]["punch"]["attempts"] == 2
        assert red["targets_landed"]["body"]["count"] == 1

        blue = stats["fighters"]["blue"]
        assert blue["totals"]["attempts"] == 1
        assert blue["totals"]["landed"] == 0
        assert blue["totals"]["accuracy"] == 0.0
        assert blue["by_round"][0]["accuracy"] is None
        assert all(entry["share"] is None for entry in blue["targets_landed"].values())

    def test_no_rounds_marked_yet(self) -> None:
        stats = fight_stats([tag()], [], scheduled_rounds=3)
        assert stats["fight_time_s"] == 0
        assert stats["rounds"] == []
        assert stats["uncounted_tags"] == 1
        totals = stats["fighters"]["red"]["totals"]
        assert totals["attempts"] == 0
        assert totals["accuracy"] is None
        assert totals["strikes_per_minute"] is None

    def test_fighters_never_mix(self) -> None:
        stats = fight_stats([tag(fighter="blue")], ROUNDS, scheduled_rounds=2)
        assert stats["fighters"]["red"]["totals"]["attempts"] == 0
        assert stats["fighters"]["blue"]["totals"]["attempts"] == 1
