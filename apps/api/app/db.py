"""Database setup: engine, session, and settings.

The database is a local SQLite file. Its default location is under data/, which
is gitignored, because tags made on Byon footage must never reach git.
"""

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy import DateTime, Engine, create_engine, event, inspect, text
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE_URL = f"sqlite:///{REPO_ROOT / 'data' / 'strikelens.db'}"
DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def database_url() -> str:
    """Database URL from STRIKELENS_DATABASE_URL, or the default file under data/."""
    return os.environ.get("STRIKELENS_DATABASE_URL", DEFAULT_DATABASE_URL)


def cors_origins() -> list[str]:
    """Allowed origins from STRIKELENS_CORS_ORIGINS (comma separated), or the local tagger."""
    raw = os.environ.get("STRIKELENS_CORS_ORIGINS")
    if raw is None:
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware datetime stored as UTC. SQLite drops the offset, so add it back."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("datetimes must be timezone-aware")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


def make_engine(url: str) -> Engine:
    """Create the engine. For a SQLite file, create its folder and turn on foreign keys."""
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False})

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(connection: Any, _record: Any) -> None:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# Columns added after the first release. `create_all` makes new tables but never
# changes existing ones, so a database from an older version gets them here.
ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("fights", "segments", "JSON NOT NULL DEFAULT '[]'"),
)


def upgrade_schema(engine: Engine) -> list[str]:
    """Add missing columns to existing tables. Returns the columns added."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    added: list[str] = []
    with engine.begin() as connection:
        for table, column, definition in ADDED_COLUMNS:
            if table not in tables:
                continue
            if column in {c["name"] for c in inspector.get_columns(table)}:
                continue
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
            added.append(f"{table}.{column}")
    return added


def get_session(request: Request) -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    factory: sessionmaker[Session] = request.app.state.sessionmaker
    with factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
