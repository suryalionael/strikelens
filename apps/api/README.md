# StrikeLens API

FastAPI service for fights, tags, and stats. SQLite locally.

```bash
uv sync
uv run uvicorn app.main:app --reload   # http://localhost:8000/health
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

- `app/routes/`: HTTP endpoints.
- `app/models/`: SQLAlchemy models and Pydantic schemas.
- `app/stats/`: pure stat functions. No database or HTTP code here.

See [docs/dev-setup.md](../../docs/dev-setup.md).
