"""Response models for GET /fights/{id}/stats. They mirror the TypedDicts in
app/stats/core.py, which hold the actual calculations."""

import uuid

from pydantic import BaseModel


class Split(BaseModel):
    attempts: int
    landed: int
    accuracy: float | None
    strikes_per_minute: float | None


class RoundSplit(Split):
    round: int


class MixEntry(BaseModel):
    attempts: int
    landed: int
    share: float | None


class TargetEntry(BaseModel):
    count: int
    share: float | None


class FighterStats(BaseModel):
    totals: Split
    by_round: list[RoundSplit]
    weapons: dict[str, MixEntry]
    weapon_groups: dict[str, MixEntry]
    targets_landed: dict[str, TargetEntry]
    targets_attempted: dict[str, TargetEntry]


class RoundInfo(BaseModel):
    number: int
    start_ms: int
    end_ms: int
    time_s: float
    partial: bool


class Fighters(BaseModel):
    red: FighterStats
    blue: FighterStats


class FightStats(BaseModel):
    fight_id: uuid.UUID
    fight_time_s: float
    rounds: list[RoundInfo]
    fighters: Fighters
    uncounted_tags: int
    segment_tags: int
    provisional_rules: list[str]
