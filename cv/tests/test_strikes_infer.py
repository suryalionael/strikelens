"""Strike suggestions: peak picking, tags in the schema, and the motion baseline."""

import json
from datetime import UTC, datetime

from strikelens_cv.paths import REPO_ROOT
from strikelens_cv.strikes.infer import pick_peaks, suggestions
from strikelens_cv.strikes.models import MotionBaseline, load_model

SCHEMA = json.loads((REPO_ROOT / "shared" / "schema" / "tag.schema.json").read_text())
FIGHT = {
    "id": "3dc929d7-0253-4c8b-b1c0-651b0f95ea3c",
    "rounds": [{"number": 1, "start_ms": 1000, "end_ms": 10_000}],
    "segments": [{"kind": "replay", "start_ms": 6000, "end_ms": 7000}],
}


def test_peaks_above_threshold_and_apart() -> None:
    times = list(range(0, 2000, 100))
    scores = [0.1] * 20
    scores[3], scores[5], scores[15] = 0.95, 0.92, 0.97
    peaks = pick_peaks(times, scores, [None] * 20, 0.9, 700)
    assert [p["timestamp_ms"] for p in peaks] == [300, 1500]  # 500 is too close to 300


def test_tags_follow_the_schema_and_skip_segments_and_outside_rounds() -> None:
    peaks = {
        "red": [{"timestamp_ms": 2000, "score": 0.93, "weapon": None}],
        "blue": [
            {"timestamp_ms": 6500, "score": 0.99, "weapon": None},  # inside a replay
            {"timestamp_ms": 12_000, "score": 0.99, "weapon": None},  # after the round
        ],
    }
    now = datetime(2026, 11, 7, tzinfo=UTC)
    [tag] = suggestions(FIGHT, peaks, "motion-baseline@1", now)
    assert set(tag) == set(SCHEMA["required"]) == set(SCHEMA["properties"])
    for field in ("fighter", "outcome", "target", "source", "status"):
        assert tag[field] in SCHEMA["properties"][field]["enum"]
    assert tag["source"] == "cv" and tag["status"] == "pending" and tag["confidence"] == 0.93
    assert tag["round"] == 1 and tag["created_by"] == "motion-baseline@1"
    assert tag["created_at"] == "2026-11-07T00:00:00Z"
    # Same inputs, same id: posting twice is refused instead of doubling.
    assert suggestions(FIGHT, peaks, "motion-baseline@1", now)[0]["id"] == tag["id"]


def still(n: int = 16) -> list[list[list[float]]]:
    return [[[0.0, 0.0, 0.0, 1.0] for _ in range(33)] for _ in range(n)]


def test_motion_baseline_scores_fast_limbs_high() -> None:
    model = load_model("motion-baseline")
    assert isinstance(model, MotionBaseline)
    fast = still()
    fast[8][15] = [0.5, 0.0, 0.0, 1.0]  # a wrist moves half a box height in one step
    calm, quick = model.predict([still(), fast], sample_ms=66.7)
    assert calm["strike"] < 0.1 and quick["strike"] > 0.9
    assert quick["weapon"] is None


def test_unknown_model_is_an_error() -> None:
    import pytest

    with pytest.raises(ValueError, match="unknown model"):
        load_model("nope")
