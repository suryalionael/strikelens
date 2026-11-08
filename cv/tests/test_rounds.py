"""Round suggestions from when the scoreboard is on screen. Synthetic samples only."""

from pathlib import Path

import pytest

from strikelens_cv.rounds import (
    RoundsConfig,
    load_rounds_config,
    suggest_rounds,
    visible_runs,
)
from strikelens_cv.rounds.config import DEFAULT_ROUNDS_CONFIG

CONFIG = RoundsConfig()
S = 1000  # one sample per second


def seen(*spans: tuple[int, int], until: int = 1200) -> list[tuple[int, bool]]:
    """One sample per second up to `until` s, on inside the given (start, end) seconds."""
    return [(t * S, any(a <= t <= b for a, b in spans)) for t in range(until)]


def test_runs_bridge_short_gaps_only() -> None:
    samples = seen((10, 20), (30, 40), (60, 70))  # gaps of 10 s and 20 s
    assert visible_runs(samples, max_gap_ms=15_000) == [(10_000, 40_000), (60_000, 70_000)]


def test_a_full_round_with_the_scoreboard_hidden_at_the_end() -> None:
    # Tryout 2, round 1: on 2:59-5:49, the clock would reach 0:00 at 5:59.
    [round_] = suggest_rounds(seen((179, 349)), 1_200_000, CONFIG)
    assert (round_["start_ms"], round_["end_ms"], round_["partial"]) == (179_000, 359_000, False)
    assert "hidden for the last seconds" in round_["reason"]


def test_a_stoppage_ends_the_round_where_the_scoreboard_goes() -> None:
    # Tryout 2, round 2: on 7:05-8:07, then a knockdown.
    [round_] = suggest_rounds(seen((425, 487)), 1_200_000, CONFIG)
    assert (round_["start_ms"], round_["end_ms"], round_["partial"]) == (425_000, 487_000, True)
    assert "a stoppage" in round_["reason"]


def test_a_round_longer_than_three_minutes_keeps_its_length() -> None:
    # The clock stopped for a foul, so the round ran 3:30 of video.
    [round_] = suggest_rounds(seen((100, 310)), 1_200_000, CONFIG)
    assert (round_["end_ms"], round_["partial"]) == (310_000, False)


def test_rounds_are_numbered_and_never_run_into_the_next() -> None:
    # Round 1 is hidden from 4:22 and would run to 4:40, but round 2's scoreboard
    # appears at 4:38 (synthetic): round 1 is cut at 4:38.
    rounds = suggest_rounds(seen((100, 262), (278, 460)), 1_200_000, CONFIG)
    assert [(r["number"], r["start_ms"], r["end_ms"]) for r in rounds] == [
        (1, 100_000, 278_000),
        (2, 278_000, 460_000),
    ]


def test_the_last_round_stops_at_the_end_of_the_video() -> None:
    [round_] = suggest_rounds(seen((1000, 1170), until=1180), 1_180_000, CONFIG)
    assert round_["end_ms"] == 1_180_000


def test_a_pause_inside_a_round_does_not_split_it() -> None:
    # Showbiz 6, round 5: on 38:45-40:08, a doctor's check hides the scoreboard
    # for 64 s, then on again 41:12-42:31 until the end.
    [round_] = suggest_rounds(seen((2325, 2408), (2472, 2551), until=3000), 3_000_000, CONFIG)
    assert (round_["start_ms"], round_["partial"]) == (2_325_000, False)
    assert round_["end_ms"] == 2_325_000 + 180_000 + 64_000
    assert "a pause of 1:04" in round_["reason"]


def test_a_stoppage_is_not_merged_with_the_next_full_round() -> None:
    # Round 2 stopped after 2 minutes; round 3 is a full round after the rest.
    rounds = suggest_rounds(seen((1000, 1118), (1200, 1367), until=1500), 1_500_000, CONFIG)
    assert [(r["start_ms"], r["end_ms"], r["partial"]) for r in rounds] == [
        (1_000_000, 1_118_000, True),
        (1_200_000, 1_380_000, False),
    ]


def test_short_sightings_are_not_rounds() -> None:
    # A replay or a promo shows the graphic for a few seconds.
    assert suggest_rounds(seen((50, 60)), 1_200_000, CONFIG) == []


def test_no_scoreboard_no_rounds() -> None:
    assert suggest_rounds(seen(), 1_200_000, CONFIG) == []


def test_default_config_file_matches_the_defaults() -> None:
    assert load_rounds_config(DEFAULT_ROUNDS_CONFIG) == CONFIG


@pytest.mark.parametrize(
    "values",
    [
        {"scoreboard_region": (0.5, 0.6, 0.4, 0.9)},
        {"scoreboard_region": (0, 0, 1, 1.5)},
        {"grid": (0, 4)},
        {"match": 1},
        {"sample_ms": 0},
        {"round_ms": 0},
        {"max_gap_ms": -1},
    ],
)
def test_bad_values(values: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        RoundsConfig(**values)  # type: ignore[arg-type]


def test_unknown_and_malformed_keys(tmp_path: Path) -> None:
    path = tmp_path / "rounds.toml"
    path.write_text("round_length = 180000\n")
    with pytest.raises(ValueError, match="round_length"):
        load_rounds_config(path)
    path.write_text("grid = [6]\n")
    with pytest.raises(ValueError, match="grid"):
        load_rounds_config(path)


@pytest.mark.usefixtures("data_dir")
def test_cli_explains_missing_ingest(capsys: pytest.CaptureFixture[str]) -> None:
    from strikelens_cv.cli import main

    assert main(["rounds", "--fight", "nothing"]) == 1
    assert "run strikelens-cv ingest first" in capsys.readouterr().err
