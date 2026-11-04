"""Example tags shared by the schema tests and the Pydantic parity tests."""

import copy
from typing import Any

HUMAN_TAG: dict[str, Any] = {
    "id": "3f1c2b8e-8a4d-4a7e-9a51-0c1d2e3f4a5b",
    "fight_id": "9b2e7c10-1d3f-4b6a-8c9d-0e1f2a3b4c5d",
    "round": 1,
    "timestamp_ms": 61250,
    "fighter": "red",
    "weapon": "kick",
    "outcome": "landed",
    "target": "body",
    "source": "human",
    "confidence": None,
    "status": "confirmed",
    "created_by": "lionael",
    "created_at": "2026-11-03T10:15:00Z",
}

CV_SUGGESTION: dict[str, Any] = {
    **HUMAN_TAG,
    "id": "7a6b5c4d-3e2f-4a1b-9c8d-7e6f5a4b3c2d",
    "weapon": "kick",
    "outcome": None,
    "target": None,
    "source": "cv",
    "confidence": 0.82,
    "status": "pending",
    "created_by": "strike-tcn@0.1.0",
}


def _with(base: dict[str, Any], **changes: Any) -> dict[str, Any]:
    tag = copy.deepcopy(base)
    tag.update(changes)
    return tag


INVALID_TAGS: dict[str, dict[str, Any]] = {
    "bad-fighter": _with(HUMAN_TAG, fighter="green"),
    "bad-weapon": _with(HUMAN_TAG, weapon="spinning_backfist"),
    "round-zero": _with(HUMAN_TAG, round=0),
    "negative-time": _with(HUMAN_TAG, timestamp_ms=-1),
    "bad-status": _with(HUMAN_TAG, status="maybe"),
    "bad-uuid": _with(HUMAN_TAG, id="not-a-uuid"),
    "extra-field": _with(HUMAN_TAG, extra_field=True),
    "cv-without-confidence": _with(CV_SUGGESTION, confidence=None),
    "confidence-above-one": _with(CV_SUGGESTION, confidence=1.5),
    "human-with-confidence": _with(HUMAN_TAG, confidence=0.9),
    "confirmed-without-outcome": _with(HUMAN_TAG, outcome=None),
    "blank-created-by": _with(HUMAN_TAG, created_by=""),
    "rejected-cv-with-confidence-below-zero": _with(
        CV_SUGGESTION, status="rejected", confidence=-0.1
    ),
}
