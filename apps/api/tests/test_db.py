from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import db
from app.main import create_app


def test_default_database_is_under_gitignored_data_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIKELENS_DATABASE_URL", raising=False)
    assert db.database_url() == f"sqlite:///{db.REPO_ROOT / 'data' / 'strikelens.db'}"


def test_database_url_can_be_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIKELENS_DATABASE_URL", "sqlite:////tmp/other.db")
    assert db.database_url() == "sqlite:////tmp/other.db"


def test_cors_origins_default_to_local_tagger(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIKELENS_CORS_ORIGINS", raising=False)
    assert db.cors_origins() == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_cors_origins_can_be_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIKELENS_CORS_ORIGINS", "http://a.test, http://b.test,")
    assert db.cors_origins() == ["http://a.test", "http://b.test"]


def test_utc_datetime_round_trips_as_utc() -> None:
    column = db.UTCDateTime()
    jakarta = datetime(2026, 11, 3, 17, 0, tzinfo=timezone(timedelta(hours=7)))
    stored = column.process_bind_param(jakarta, None)  # type: ignore[arg-type]
    assert stored == datetime(2026, 11, 3, 10, 0)
    assert column.process_result_value(stored, None) == datetime(2026, 11, 3, 10, 0, tzinfo=UTC)  # type: ignore[arg-type]


def test_utc_datetime_rejects_naive_values() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        db.UTCDateTime().process_bind_param(datetime(2026, 11, 3), None)  # type: ignore[arg-type]


# The fights table as it was before segments were added (#18).
OLD_FIGHTS_TABLE = """
CREATE TABLE fights (
    id CHAR(32) PRIMARY KEY,
    event VARCHAR NOT NULL,
    date DATE NOT NULL,
    red_fighter_id CHAR(32) NOT NULL,
    blue_fighter_id CHAR(32) NOT NULL,
    weight_class VARCHAR,
    scheduled_rounds INTEGER NOT NULL,
    video_file VARCHAR,
    rounds JSON NOT NULL,
    result JSON
)
"""


def test_upgrade_adds_segments_to_an_old_database(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'old.db'}"
    engine = db.make_engine(url)
    with engine.begin() as connection:
        connection.execute(text(OLD_FIGHTS_TABLE))
        connection.execute(
            text(
                "INSERT INTO fights VALUES ('9b2e7c101d3f4b6a8c9d0e1f2a3b4c5d', 'Old Event',"
                " '2026-11-01', '1b9d6bcdbbfd4b2d9b5dab8dfbbd4bed',"
                " '6ec0bd7f11c043da975e2a8ad9ebae0b', NULL, 3, NULL, '[]', NULL)"
            )
        )

    assert db.upgrade_schema(engine) == ["fights.segments"]
    assert db.upgrade_schema(engine) == []
    engine.dispose()

    with TestClient(create_app(url)) as client:
        response = client.get("/fights/9b2e7c10-1d3f-4b6a-8c9d-0e1f2a3b4c5d")
    assert response.status_code == 200, response.text
    assert response.json()["segments"] == []


def test_upgrade_skips_a_new_database(tmp_path: Path) -> None:
    engine = db.make_engine(f"sqlite:///{tmp_path / 'new.db'}")
    assert db.upgrade_schema(engine) == []
