"""SQLAlchemy tables. Column names match the shared JSON Schemas."""

import uuid
from datetime import date as Date
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UTCDateTime


class FighterRow(Base):
    __tablename__ = "fighters"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    nickname: Mapped[str | None] = mapped_column(String)
    gym: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String(2))


class FightRow(Base):
    __tablename__ = "fights"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    event: Mapped[str] = mapped_column(String)
    date: Mapped[Date] = mapped_column(sa.Date)
    red_fighter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fighters.id"))
    blue_fighter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fighters.id"))
    weight_class: Mapped[str | None] = mapped_column(String)
    scheduled_rounds: Mapped[int] = mapped_column(Integer)
    video_file: Mapped[str | None] = mapped_column(String)
    # Rounds, segments, and result are always read and written with their fight, so
    # they are stored as JSON instead of separate tables.
    rounds: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    segments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class TagRow(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    fight_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fights.id", ondelete="CASCADE"), index=True
    )
    round: Mapped[int] = mapped_column(Integer)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    fighter: Mapped[str] = mapped_column(String)
    weapon: Mapped[str | None] = mapped_column(String)
    outcome: Mapped[str | None] = mapped_column(String)
    target: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, index=True)
    created_by: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
