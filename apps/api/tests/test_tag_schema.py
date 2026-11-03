"""Validate shared/schema/tag.schema.json and check it accepts and rejects the right tags."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "shared" / "schema"


def _load(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text())


TAG_SCHEMA = _load("tag.schema.json")
VALIDATOR = Draft202012Validator(TAG_SCHEMA, format_checker=FormatChecker())

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


@pytest.mark.parametrize("name", ["tag.schema.json", "fight.schema.json", "fighter.schema.json"])
def test_schemas_are_valid_draft_2020_12(name: str) -> None:
    Draft202012Validator.check_schema(_load(name))


def test_human_tag_is_valid() -> None:
    VALIDATOR.validate(HUMAN_TAG)


def test_pending_cv_suggestion_is_valid() -> None:
    VALIDATOR.validate(CV_SUGGESTION)


@pytest.mark.parametrize(
    "bad",
    [
        _with(HUMAN_TAG, fighter="green"),
        _with(HUMAN_TAG, weapon="spinning_backfist"),
        _with(HUMAN_TAG, round=0),
        _with(HUMAN_TAG, timestamp_ms=-1),
        _with(HUMAN_TAG, status="maybe"),
        _with(HUMAN_TAG, id="not-a-uuid"),
        _with(HUMAN_TAG, extra_field=True),
        _with(CV_SUGGESTION, confidence=None),
        _with(CV_SUGGESTION, confidence=1.5),
        _with(HUMAN_TAG, confidence=0.9),
        _with(HUMAN_TAG, outcome=None),
    ],
    ids=[
        "bad-fighter",
        "bad-weapon",
        "round-zero",
        "negative-time",
        "bad-status",
        "bad-uuid",
        "extra-field",
        "cv-without-confidence",
        "confidence-above-one",
        "human-with-confidence",
        "confirmed-without-outcome",
    ],
)
def test_invalid_tags_are_rejected(bad: dict[str, Any]) -> None:
    assert not VALIDATOR.is_valid(bad)


@pytest.mark.parametrize("field", TAG_SCHEMA["required"])
def test_missing_required_field_is_rejected(field: str) -> None:
    tag = copy.deepcopy(HUMAN_TAG)
    del tag[field]
    assert not VALIDATOR.is_valid(tag)
