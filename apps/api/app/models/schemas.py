"""Pydantic models that mirror shared/schema/*.json.

The JSON Schemas are the source of truth. tests/test_models_match_schema.py runs
the same valid and invalid examples through both and checks they agree.

Create models make `id` optional (the API generates one) so the tagger and the
CV pipeline can either send their own UUIDs or let the server pick.
"""

import uuid
from datetime import UTC, datetime
from datetime import date as Date
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

Corner = Literal["red", "blue"]
Weapon = Literal["jab", "cross", "hook", "uppercut", "kick", "knee", "elbow", "teep"]
Outcome = Literal["landed", "missed", "blocked"]
Target = Literal["head", "body", "legs"]
Source = Literal["human", "cv"]
Status = Literal["pending", "confirmed", "rejected"]
Winner = Literal["red", "blue", "draw", "no_contest"]
SegmentKind = Literal["replay", "non_fight"]

NonEmpty = Annotated[str, StringConstraints(min_length=1)]
CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]


def _require_utc_offset(value: datetime) -> datetime:
    # JSON Schema date-time requires an offset; a naive time is ambiguous.
    if value.tzinfo is None:
        raise ValueError("created_at must include a timezone offset")
    return value.astimezone(UTC)


AwareDatetime = Annotated[datetime, AfterValidator(_require_utc_offset)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


# Fighters


class FighterFields(StrictModel):
    name: NonEmpty
    nickname: str | None = None
    gym: str | None = None
    country: CountryCode | None = None


class FighterCreate(FighterFields):
    id: uuid.UUID | None = None


class FighterUpdate(StrictModel):
    name: NonEmpty | None = None
    nickname: str | None = None
    gym: str | None = None
    country: CountryCode | None = None


class Fighter(FighterFields):
    id: uuid.UUID


# Fights


class Round(StrictModel):
    number: int = Field(ge=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)


class Segment(StrictModel):
    """A replay or non-fight stretch of video. `end_ms` is exclusive."""

    kind: SegmentKind
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)


class Result(StrictModel):
    winner: Winner | None = None
    method: str | None = None
    round: int | None = Field(default=None, ge=1)


class FightFields(StrictModel):
    event: NonEmpty
    date: Date
    red_fighter_id: uuid.UUID
    blue_fighter_id: uuid.UUID
    weight_class: str | None = None
    scheduled_rounds: int = Field(ge=1)
    video_file: str | None = None
    rounds: list[Round] = Field(default_factory=list)
    segments: list[Segment] = Field(default_factory=list)
    result: Result | None = None

    @model_validator(mode="after")
    def _different_fighters(self) -> Self:
        if self.red_fighter_id == self.blue_fighter_id:
            raise ValueError("red and blue fighters must be different")
        return self

    @model_validator(mode="after")
    def _valid_rounds(self) -> Self:
        """Rules the JSON Schema cannot express. See docs/stat-definitions.md (Time)."""
        if len(self.rounds) > self.scheduled_rounds:
            raise ValueError(f"more rounds than scheduled ({self.scheduled_rounds})")
        previous: Round | None = None
        for expected, r in enumerate(self.rounds, start=1):
            if r.number != expected:
                raise ValueError("rounds must be numbered 1, 2, 3, ... in order")
            if r.end_ms <= r.start_ms:
                raise ValueError(f"round {r.number} ends before it starts")
            if previous is not None and r.start_ms < previous.end_ms:
                raise ValueError(f"round {r.number} starts before round {previous.number} ends")
            previous = r
        return self

    @model_validator(mode="after")
    def _valid_segments(self) -> Self:
        """Segments run forward, in order, without overlapping. They may overlap rounds."""
        previous: Segment | None = None
        for s in self.segments:
            if s.end_ms <= s.start_ms:
                raise ValueError(f"segment at {s.start_ms} ms ends before it starts")
            if previous is not None and s.start_ms < previous.end_ms:
                raise ValueError(f"segment at {s.start_ms} ms overlaps the one before it")
            previous = s
        return self


class FightCreate(FightFields):
    id: uuid.UUID | None = None


class Fight(FightFields):
    id: uuid.UUID


# Tags


class TagFields(StrictModel):
    round: int = Field(ge=1)
    timestamp_ms: int = Field(ge=0)
    fighter: Corner
    weapon: Weapon | None
    outcome: Outcome | None
    target: Target | None
    source: Source
    confidence: float | None = Field(ge=0, le=1)
    status: Status
    created_by: NonEmpty

    @model_validator(mode="after")
    def _schema_rules(self) -> Self:
        """The allOf rules in tag.schema.json."""
        if self.source == "cv" and self.confidence is None:
            raise ValueError("CV tags need a confidence")
        if self.source == "human" and self.confidence is not None:
            raise ValueError("human tags must have a null confidence")
        # The target is optional (ADR 0010): Freefly's breakdowns do not use it.
        if self.status == "confirmed" and None in (self.weapon, self.outcome):
            raise ValueError("confirmed tags need a weapon and an outcome")
        return self


class TagCreate(TagFields):
    id: uuid.UUID | None = None
    created_at: AwareDatetime | None = None


class TagUpdate(StrictModel):
    """Fields an analyst can change. Source, confidence, and authorship are fixed."""

    round: int | None = Field(default=None, ge=1)
    timestamp_ms: int | None = Field(default=None, ge=0)
    fighter: Corner | None = None
    weapon: Weapon | None = None
    outcome: Outcome | None = None
    target: Target | None = None
    status: Status | None = None


class Tag(TagFields):
    id: uuid.UUID
    fight_id: uuid.UUID
    created_at: AwareDatetime
