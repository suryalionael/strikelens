"""CRUD for fighters."""

import uuid

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import or_, select

from app.db import SessionDep
from app.models.schemas import Fighter, FighterCreate, FighterUpdate
from app.models.tables import FighterRow, FightRow
from app.routes.common import get_or_404, validate_or_422

router = APIRouter(prefix="/fighters", tags=["fighters"])


@router.get("")
def list_fighters(session: SessionDep) -> list[Fighter]:
    rows = session.scalars(select(FighterRow).order_by(FighterRow.name))
    return [Fighter.model_validate(row) for row in rows]


@router.post("", status_code=201)
def create_fighter(body: FighterCreate, session: SessionDep) -> Fighter:
    fighter_id = body.id or uuid.uuid4()
    if session.get(FighterRow, fighter_id) is not None:
        raise HTTPException(status_code=409, detail="fighter id already exists")
    row = FighterRow(**body.model_dump(exclude={"id"}), id=fighter_id)
    session.add(row)
    session.commit()
    return Fighter.model_validate(row)


@router.get("/{fighter_id}")
def get_fighter(fighter_id: uuid.UUID, session: SessionDep) -> Fighter:
    return Fighter.model_validate(get_or_404(session, FighterRow, fighter_id, "fighter"))


@router.patch("/{fighter_id}")
def update_fighter(fighter_id: uuid.UUID, body: FighterUpdate, session: SessionDep) -> Fighter:
    row = get_or_404(session, FighterRow, fighter_id, "fighter")
    merged = validate_or_422(
        Fighter, {**Fighter.model_validate(row).model_dump(), **body.model_dump(exclude_unset=True)}
    )
    for field, value in merged.model_dump(exclude={"id"}).items():
        setattr(row, field, value)
    session.commit()
    return merged


@router.delete("/{fighter_id}", status_code=204)
def delete_fighter(fighter_id: uuid.UUID, session: SessionDep) -> Response:
    row = get_or_404(session, FighterRow, fighter_id, "fighter")
    in_use = session.scalar(
        select(FightRow.id).where(
            or_(FightRow.red_fighter_id == fighter_id, FightRow.blue_fighter_id == fighter_id)
        )
    )
    if in_use is not None:
        raise HTTPException(status_code=409, detail="fighter is in a fight; delete the fight first")
    session.delete(row)
    session.commit()
    return Response(status_code=204)
