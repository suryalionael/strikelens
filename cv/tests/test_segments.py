"""Replay suggestions and segment filtering. Pure functions, no extras needed."""

import json
from pathlib import Path

import pytest

from strikelens_cv.ingest.cuts import Shot
from strikelens_cv.segments import (
    DEFAULT_SEGMENT_CONFIG,
    SegmentConfig,
    frames_outside,
    in_segment,
    load_segment_config,
    load_segments,
    parse_segments,
    suggest,
    suggest_segments,
)

CONFIG = SegmentConfig(short_shot_ms=2_000, min_run=3)


def shots(*lengths_ms: int) -> list[Shot]:
    """Back-to-back shots with the given lengths, starting at 0."""
    out: list[Shot] = []
    start = 0
    for index, length in enumerate(lengths_ms):
        out.append({"index": index, "start_ms": start, "end_ms": start + length})
        start += length
    return out


class TestSuggest:
    def test_no_shots(self) -> None:
        assert suggest_segments([], CONFIG) == []

    def test_long_shots_only(self) -> None:
        assert suggest_segments(shots(60_000, 30_000), CONFIG) == []

    def test_run_too_short(self) -> None:
        assert suggest_segments(shots(60_000, 1_000, 1_000, 60_000), CONFIG) == []

    def test_run_in_the_middle(self) -> None:
        result = suggest_segments(shots(60_000, 1_000, 1_500, 500, 60_000), CONFIG)
        assert result == [
            {
                "kind": "replay",
                "start_ms": 60_000,
                "end_ms": 63_000,
                "reason": "3 shots in a row, each under 2 s",
            }
        ]

    def test_runs_at_the_start_and_end(self) -> None:
        result = suggest_segments(shots(1_000, 1_000, 1_000, 60_000, 1_000, 1_000, 1_000), CONFIG)
        assert [(s["start_ms"], s["end_ms"]) for s in result] == [(0, 3_000), (63_000, 66_000)]

    def test_a_shot_exactly_at_the_limit_is_not_short(self) -> None:
        assert suggest_segments(shots(1_000, 2_000, 1_000), CONFIG) == []

    def test_min_run_of_one(self) -> None:
        result = suggest_segments(shots(60_000, 1_000), SegmentConfig(2_000, min_run=1))
        assert [(s["start_ms"], s["end_ms"]) for s in result] == [(60_000, 61_000)]


class TestConfig:
    def test_default_file_matches_the_defaults(self) -> None:
        assert load_segment_config(DEFAULT_SEGMENT_CONFIG) == SegmentConfig()

    def test_unknown_key_is_an_error(self, tmp_path: Path) -> None:
        path = tmp_path / "segments.toml"
        path.write_text("min_runs = 2\n")
        with pytest.raises(ValueError, match="min_runs"):
            load_segment_config(path)

    @pytest.mark.parametrize("values", [{"short_shot_ms": 0}, {"min_run": 0}])
    def test_bad_values(self, values: dict[str, int]) -> None:
        with pytest.raises(ValueError):
            SegmentConfig(**values)


REPLAY = {"kind": "replay", "start_ms": 1_000, "end_ms": 2_000}


class TestFilter:
    def test_end_is_exclusive(self) -> None:
        assert in_segment(1_000, [REPLAY])  # type: ignore[list-item]
        assert in_segment(1_999, [REPLAY])  # type: ignore[list-item]
        assert not in_segment(2_000, [REPLAY])  # type: ignore[list-item]

    def test_frames_outside_skips_frames_in_segments(self) -> None:
        frames = [{"index": i, "file": f"{i:06}.jpg", "timestamp_ms": i * 500} for i in range(6)]
        segments = parse_segments({"segments": [REPLAY]})
        kept = frames_outside(frames, segments)
        assert [f["timestamp_ms"] for f in kept] == [0, 500, 2_000, 2_500]

    def test_no_segments_keeps_every_frame(self) -> None:
        frames = [{"timestamp_ms": 0}, {"timestamp_ms": 100}]
        assert frames_outside(frames, []) == frames


class TestLoad:
    def test_fight_without_segments(self) -> None:
        assert parse_segments({"rounds": []}) == []

    def test_sorted_by_start(self) -> None:
        later = {"kind": "non_fight", "start_ms": 5_000, "end_ms": 6_000}
        assert parse_segments({"segments": [later, REPLAY]}) == [REPLAY, later]

    @pytest.mark.parametrize(
        "bad",
        [
            {"segments": "none"},
            {"segments": [{"kind": "slow_motion", "start_ms": 0, "end_ms": 1}]},
            {"segments": [{"kind": "replay", "start_ms": 5, "end_ms": 5}]},
            {"segments": [{"kind": "replay", "start_ms": 0.5, "end_ms": 5}]},
        ],
        ids=["not-a-list", "bad-kind", "zero-length", "not-whole-ms"],
    )
    def test_rejects_bad_segments(self, bad: dict[str, object]) -> None:
        with pytest.raises(ValueError):
            parse_segments(bad)

    def test_load_from_saved_fight(self, tmp_path: Path) -> None:
        path = tmp_path / "fight.json"
        path.write_text(json.dumps({"id": "x", "segments": [REPLAY]}))
        assert load_segments(path) == [REPLAY]


class TestSuggestFromCuts:
    def test_writes_suggestions_next_to_cuts(self, data_dir: Path) -> None:
        out = data_dir / "processed" / "fight"
        out.mkdir(parents=True)
        (out / "cuts.json").write_text(
            json.dumps({"duration_ms": 66_000, "shots": shots(60_000, 1_000, 1_000, 1_000)})
        )
        path, result = suggest("Fight", CONFIG)
        assert path == out / "segment-suggestions.json"
        assert len(result) == 1
        written = json.loads(path.read_text())
        assert written["config"] == {"short_shot_ms": 2_000, "min_run": 3}
        assert written["suggestions"] == result

    def test_needs_a_cut_list(self, data_dir: Path) -> None:
        with pytest.raises(FileNotFoundError, match="ingest first"):
            suggest("fight", CONFIG)
