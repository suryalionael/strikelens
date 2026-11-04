# StrikeLens API

FastAPI service for fighters, fights, tags, and stats. SQLite locally.

```bash
uv sync
uv run uvicorn app.main:app --reload   # http://localhost:8000/health, docs at /docs
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

- `app/routes/`: HTTP endpoints.
- `app/models/`: SQLAlchemy tables and Pydantic schemas.
- `app/stats/`: pure stat functions. No database or HTTP code here.
- `app/db.py`: engine, sessions, and settings.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET, POST | `/fighters` | List (by name) or create fighters |
| GET, PATCH, DELETE | `/fighters/{id}` | Read, change, or delete a fighter (409 while in a fight) |
| GET, POST | `/fights` | List (newest first) or create fights |
| GET, PUT, DELETE | `/fights/{id}` | Read, replace (for example to save rounds), or delete a fight and its tags |
| GET, POST | `/fights/{id}/tags` | List tags in video order, or create one. Filter with `?status=` and `?source=` |
| POST | `/fights/{id}/tags/bulk` | Create many tags at once, all or nothing. For CV suggestions |
| GET, PATCH, DELETE | `/fights/{id}/tags/{tag_id}` | Read, change (for example confirm a suggestion), or delete a tag |
| GET | `/fights/{id}/stats` | Every v1 stat for both fighters, plus the provisional rules in use. See [docs/stat-definitions.md](../../docs/stat-definitions.md) |

Create requests may leave out `id` (the server makes a UUID) and, for tags,
`created_at` (the server uses the current UTC time). Every tag is checked with the
rules in `shared/schema/tag.schema.json`, also after a PATCH. A PATCH cannot change
`source`, `confidence`, or `created_by`.

Fights must name two different, existing fighters. Rounds must be numbered 1, 2,
3 in order, end after they start, not overlap, and not outnumber `scheduled_rounds`.

Tables are created on startup. There are no migrations yet; while the schema
changes, delete the local database file to start fresh.

## Settings

| Variable | Default | Use |
|---|---|---|
| `STRIKELENS_DATABASE_URL` | `sqlite:///<repo>/data/strikelens.db` | Database location. The default folder is gitignored |
| `STRIKELENS_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated origins allowed to call the API |

Tests use a temporary database (see `tests/conftest.py`) and never touch `data/`.

See [docs/dev-setup.md](../../docs/dev-setup.md).
