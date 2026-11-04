from datetime import UTC, datetime, timedelta, timezone

import pytest

from app import db


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
