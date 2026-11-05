"""CRUD for fights. Rounds, segments, and result are part of the fight."""

import uuid

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionDep
from app.models.schemas import Fight, FightCreate, FightFields
from app.models.tables import FighterRow, FightRow
from app.routes.common import get_or_404

router = APIRouter(prefix="/fights", tags=["fights"])


def _check_fighters_exist(session: Session, fight: FightFields) -> None:
    for fighter_id in (fight.red_fighter_id, fight.blue_fighter_id):
        if session.get(FighterRow, fighter_id) is None:
            raise HTTPException(status_code=422, detail=f"fighter {fighter_id} does not exist")


def _columns(fight: FightFields) -> dict[str, object]:
    return fight.model_dump(mode="python", exclude={"id", "rounds", "segments", "result"}) | {
        "rounds": [r.model_dump() for r in fight.rounds],
        "segments": [s.model_dump() for s in fight.segments],
        "result": fight.result.model_dump() if fight.result else None,
    }


@router.get("")
def list_fights(session: SessionDep) -> list[Fight]:
    rows = session.scalars(select(FightRow).order_by(FightRow.date.desc(), FightRow.event))
    return [Fight.model_validate(row) for row in rows]


@router.post("", status_code=201)
def create_fight(body: FightCreate, session: SessionDep) -> Fight:
    fight_id = body.id or uuid.uuid4()
    if session.get(FightRow, fight_id) is not None:
        raise HTTPException(status_code=409, detail="fight id already exists")
    _check_fighters_exist(session, body)
    row = FightRow(id=fight_id, **_columns(body))
    session.add(row)
    session.commit()
    return Fight.model_validate(row)


@router.get("/{fight_id}")
def get_fight(fight_id: uuid.UUID, session: SessionDep) -> Fight:
    return Fight.model_validate(get_or_404(session, FightRow, fight_id, "fight"))


@router.put("/{fight_id}")
def replace_fight(fight_id: uuid.UUID, body: FightFields, session: SessionDep) -> Fight:
    """Replace a fight. Used to save rounds and segments as the analyst marks them."""
    row = get_or_404(session, FightRow, fight_id, "fight")
    _check_fighters_exist(session, body)
    for field, value in _columns(body).items():
        setattr(row, field, value)
    session.commit()
    return Fight.model_validate(row)


@router.delete("/{fight_id}", status_code=204)
def delete_fight(fight_id: uuid.UUID, session: SessionDep) -> Response:
    """Delete a fight and all its tags."""
    session.delete(get_or_404(session, FightRow, fight_id, "fight"))
    session.commit()
    return Response(status_code=204)
