"""The Pydantic models must accept and reject exactly what the JSON Schemas do."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, ValidationError

from app.models.schemas import Fight, Fighter, Tag
from tests.tag_cases import CV_SUGGESTION, HUMAN_TAG, INVALID_TAGS

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "shared" / "schema"


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / name).read_text())
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _pydantic_accepts(model: type[BaseModel], data: dict[str, Any]) -> bool:
    try:
        model.model_validate(data)
    except ValidationError:
        return False
    return True


TAG_VALIDATOR = _validator("tag.schema.json")

TAG_CASES = {"human": HUMAN_TAG, "cv-pending": CV_SUGGESTION, **INVALID_TAGS}
for _field in TAG_VALIDATOR.schema["required"]:
    TAG_CASES[f"missing-{_field}"] = {k: v for k, v in HUMAN_TAG.items() if k != _field}


@pytest.mark.parametrize("data", TAG_CASES.values(), ids=TAG_CASES.keys())
def test_tag_model_agrees_with_schema(data: dict[str, Any]) -> None:
    assert _pydantic_accepts(Tag, data) == TAG_VALIDATOR.is_valid(data)


def test_tag_model_rejects_time_without_offset() -> None:
    assert not _pydantic_accepts(Tag, {**HUMAN_TAG, "created_at": "2026-11-03T10:15:00"})


FIGHTER = {"id": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed", "name": "Red Fighter"}
FIGHTER_CASES: dict[str, dict[str, Any]] = {
    "minimal": FIGHTER,
    "full": {**FIGHTER, "nickname": None, "gym": "Gym A", "country": "ID"},
    "lowercase-country": {**FIGHTER, "country": "id"},
    "blank-name": {**FIGHTER, "name": ""},
    "no-name": {"id": FIGHTER["id"]},
    "extra-field": {**FIGHTER, "corner": "red"},
}


@pytest.mark.parametrize("data", FIGHTER_CASES.values(), ids=FIGHTER_CASES.keys())
def test_fighter_model_agrees_with_schema(data: dict[str, Any]) -> None:
    assert _pydantic_accepts(Fighter, data) == _validator("fighter.schema.json").is_valid(data)


FIGHT: dict[str, Any] = {
    "id": "9b2e7c10-1d3f-4b6a-8c9d-0e1f2a3b4c5d",
    "event": "Test Event 1",
    "date": "2026-11-01",
    "red_fighter_id": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed",
    "blue_fighter_id": "6ec0bd7f-11c0-43da-975e-2a8ad9ebae0b",
    "scheduled_rounds": 3,
    "rounds": [{"number": 1, "start_ms": 1000, "end_ms": 181000}],
}


def _fight(**changes: Any) -> dict[str, Any]:
    fight = copy.deepcopy(FIGHT)
    fight.update(changes)
    return fight


FIGHT_CASES: dict[str, dict[str, Any]] = {
    "minimal": FIGHT,
    "with-result": _fight(result={"winner": "red", "method": "KO", "round": 1}),
    "zero-rounds-scheduled": _fight(scheduled_rounds=0),
    "bad-winner": _fight(result={"winner": "green"}),
    "round-zero": _fight(rounds=[{"number": 0, "start_ms": 0, "end_ms": 1}]),
    "round-extra-field": _fight(rounds=[{"number": 1, "start_ms": 0, "end_ms": 1, "x": 1}]),
    "no-rounds-field": {k: v for k, v in FIGHT.items() if k != "rounds"},
    "with-segments": _fight(
        segments=[
            {"kind": "replay", "start_ms": 60_000, "end_ms": 70_000},
            {"kind": "non_fight", "start_ms": 181_000, "end_ms": 200_000},
        ]
    ),
    "empty-segments": _fight(segments=[]),
    "segment-bad-kind": _fight(segments=[{"kind": "slow_motion", "start_ms": 0, "end_ms": 1}]),
    "segment-no-end": _fight(segments=[{"kind": "replay", "start_ms": 0}]),
    "segment-negative": _fight(segments=[{"kind": "replay", "start_ms": -1, "end_ms": 1}]),
    "segment-extra-field": _fight(
        segments=[{"kind": "replay", "start_ms": 0, "end_ms": 1, "reason": "x"}]
    ),
}


@pytest.mark.parametrize("data", FIGHT_CASES.values(), ids=FIGHT_CASES.keys())
def test_fight_model_agrees_with_schema(data: dict[str, Any]) -> None:
    accepted = _pydantic_accepts(Fight, data)
    if data is FIGHT_CASES["no-rounds-field"]:
        # The API fills in an empty list, so it accepts what the schema calls incomplete.
        assert accepted
        assert Fight.model_validate(data).rounds == []
        return
    assert accepted == _validator("fight.schema.json").is_valid(data)


def test_fight_model_rejects_same_fighter_in_both_corners() -> None:
    assert not _pydantic_accepts(Fight, _fight(blue_fighter_id=FIGHT["red_fighter_id"]))
