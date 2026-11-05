"""Stats for one fight. All maths lives in app/stats/core.py."""

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.db import SessionDep
from app.models.stats import FightStats
from app.models.tables import FightRow, TagRow
from app.routes.common import get_or_404
from app.stats import core

router = APIRouter(prefix="/fights/{fight_id}/stats", tags=["stats"])

TAG_FIELDS = ("fighter", "round", "timestamp_ms", "weapon", "outcome", "target", "status")


@router.get("")
def get_fight_stats(fight_id: uuid.UUID, session: SessionDep) -> FightStats:
    """Every v1 stat for both fighters, from confirmed tags inside marked rounds and
    outside segments."""
    fight = get_or_404(session, FightRow, fight_id, "fight")
    rows = session.scalars(select(TagRow).where(TagRow.fight_id == fight_id))
    tags = [{field: getattr(row, field) for field in TAG_FIELDS} for row in rows]
    stats = core.fight_stats(tags, fight.rounds, fight.scheduled_rounds, fight.segments)
    return FightStats.model_validate(
        {**stats, "fight_id": fight_id, "provisional_rules": list(core.PROVISIONAL_RULES)}
    )
