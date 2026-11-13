"""Validate shared/schema/tag.schema.json and check it accepts and rejects the right tags."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from tests.tag_cases import CONFIRMED_WITHOUT_TARGET, CV_SUGGESTION, HUMAN_TAG, INVALID_TAGS

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "shared" / "schema"


def _load(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text())


TAG_SCHEMA = _load("tag.schema.json")
VALIDATOR = Draft202012Validator(TAG_SCHEMA, format_checker=FormatChecker())


@pytest.mark.parametrize("name", ["tag.schema.json", "fight.schema.json", "fighter.schema.json"])
def test_schemas_are_valid_draft_2020_12(name: str) -> None:
    Draft202012Validator.check_schema(_load(name))


def test_human_tag_is_valid() -> None:
    VALIDATOR.validate(HUMAN_TAG)


def test_confirmed_tag_without_a_target_is_valid() -> None:
    VALIDATOR.validate(CONFIRMED_WITHOUT_TARGET)


def test_pending_cv_suggestion_is_valid() -> None:
    VALIDATOR.validate(CV_SUGGESTION)


@pytest.mark.parametrize("bad", INVALID_TAGS.values(), ids=INVALID_TAGS.keys())
def test_invalid_tags_are_rejected(bad: dict[str, Any]) -> None:
    assert not VALIDATOR.is_valid(bad)


@pytest.mark.parametrize("field", TAG_SCHEMA["required"])
def test_missing_required_field_is_rejected(field: str) -> None:
    tag = copy.deepcopy(HUMAN_TAG)
    del tag[field]
    assert not VALIDATOR.is_valid(tag)
