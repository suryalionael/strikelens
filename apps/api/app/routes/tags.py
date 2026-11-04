"""CRUD for the tags of one fight, plus bulk create for CV suggestions."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionDep
from app.models.schemas import Source, Status, Tag, TagCreate, TagUpdate
from app.models.tables import FightRow, TagRow
from app.routes.common import get_or_404, validate_or_422

router = APIRouter(prefix="/fights/{fight_id}/tags", tags=["tags"])

# One fight has a few hundred human tags; CV can suggest more. This cap only
# stops a runaway request.
MAX_BULK_TAGS = 10_000


def _new_row(fight_id: uuid.UUID, body: TagCreate) -> TagRow:
    tag = Tag(
        **body.model_dump(exclude={"id", "created_at"}),
        id=body.id or uuid.uuid4(),
        fight_id=fight_id,
        created_at=body.created_at or datetime.now(UTC),
    )
    return TagRow(**tag.model_dump())


def _get_tag(session: Session, fight_id: uuid.UUID, tag_id: uuid.UUID) -> TagRow:
    row = session.get(TagRow, tag_id)
    if row is None or row.fight_id != fight_id:
        raise HTTPException(status_code=404, detail="tag not found")
    return row


def _insert(session: Session, rows: list[TagRow]) -> list[Tag]:
    ids = [row.id for row in rows]
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=409, detail="duplicate tag ids in request")
    if session.scalar(select(TagRow.id).where(TagRow.id.in_(ids)).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="tag id already exists")
    session.add_all(rows)
    session.commit()
    return [Tag.model_validate(row) for row in rows]


@router.get("")
def list_tags(
    fight_id: uuid.UUID,
    session: SessionDep,
    status: Status | None = None,
    source: Source | None = None,
) -> list[Tag]:
    """Tags of a fight in video order, optionally filtered by status and source."""
    get_or_404(session, FightRow, fight_id, "fight")
    query = select(TagRow).where(TagRow.fight_id == fight_id)
    if status is not None:
        query = query.where(TagRow.status == status)
    if source is not None:
        query = query.where(TagRow.source == source)
    rows = session.scalars(query.order_by(TagRow.timestamp_ms, TagRow.created_at))
    return [Tag.model_validate(row) for row in rows]


@router.post("", status_code=201)
def create_tag(fight_id: uuid.UUID, body: TagCreate, session: SessionDep) -> Tag:
    get_or_404(session, FightRow, fight_id, "fight")
    return _insert(session, [_new_row(fight_id, body)])[0]


@router.post("/bulk", status_code=201)
def create_tags_bulk(
    fight_id: uuid.UUID,
    body: list[TagCreate],
    session: SessionDep,
) -> list[Tag]:
    """Create many tags at once, all or nothing. Used by the CV pipeline for suggestions."""
    if len(body) > MAX_BULK_TAGS:
        raise HTTPException(status_code=413, detail=f"at most {MAX_BULK_TAGS} tags per request")
    get_or_404(session, FightRow, fight_id, "fight")
    return _insert(session, [_new_row(fight_id, tag) for tag in body])


@router.get("/{tag_id}")
def get_tag(fight_id: uuid.UUID, tag_id: uuid.UUID, session: SessionDep) -> Tag:
    return Tag.model_validate(_get_tag(session, fight_id, tag_id))


@router.patch("/{tag_id}")
def update_tag(
    fight_id: uuid.UUID,
    tag_id: uuid.UUID,
    body: TagUpdate,
    session: SessionDep,
) -> Tag:
    """Change some fields, for example confirm a suggestion. The result must still be valid."""
    row = _get_tag(session, fight_id, tag_id)
    current = Tag.model_validate(row).model_dump()
    merged = validate_or_422(Tag, current | body.model_dump(exclude_unset=True))
    for field, value in merged.model_dump().items():
        setattr(row, field, value)
    session.commit()
    return merged


@router.delete("/{tag_id}", status_code=204)
def delete_tag(fight_id: uuid.UUID, tag_id: uuid.UUID, session: SessionDep) -> Response:
    session.delete(_get_tag(session, fight_id, tag_id))
    session.commit()
    return Response(status_code=204)
