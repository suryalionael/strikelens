# StrikeLens

Human-in-the-loop fight analytics for kickboxing. Analysts tag strikes with
hotkeys, a CV model suggests likely strike moments, and confirmed tags turn into
stats and Instagram-ready stat cards. v1 targets Byon Combat footage, built for a
collaboration pitch to Freefly Metrics (@freefly.combat).

Owner: Lionael Surya (`suryalionael`). Works on this 8-10 hours a week.

## Stack

- `apps/tagger`: React 19, Vite, TypeScript (strict), Tailwind v4, Recharts, Vitest, ESLint, Prettier.
- `apps/api`: FastAPI, Pydantic v2, SQLAlchemy, SQLite, pytest, Ruff. Managed with uv.
- `cv`: Python package `strikelens_cv`. FFmpeg, OpenCV, PySceneDetect, YOLO + ByteTrack,
  MediaPipe, PyTorch. Heavy deps are optional extras, never installed in CI.
- `shared/schema`: JSON Schemas (Draft 2020-12) for tag, fight, fighter.

## Hard rules

1. **Never commit footage, frames, keypoints, labels, or model weights.** Everything
   under `data/` and `models/` is gitignored. Byon owns the footage; Freefly owns their tags.
2. **Never invent stat definitions.** If a counting rule is not settled in
   `docs/stat-definitions.md`, add it there as an open question for Freefly.
3. **Stat calculations are pure functions with unit tests.** No stat logic in UI components.
4. **One shared tag schema** (`shared/schema/tag.schema.json`). A CV suggestion is a tag
   with `source: "cv"`, a `confidence`, and `status: "pending" | "confirmed" | "rejected"`.
5. **Run lint and tests before saying a task is done.**
6. **One feature per branch**, named `feat/<issue-number>-<short-name>`. Conventional
   Commits. PRs include `Closes #N`.
7. **Keep it free to run.** No paid services.

## Folder map

```
apps/tagger/src/{player,fight,tagging,stats,export}/   UI by feature
apps/tagger/src/api/    typed API client and types mirroring the schemas
apps/api/app/routes/    HTTP endpoints
apps/api/app/models/    SQLAlchemy + Pydantic models
apps/api/app/stats/     pure stat functions (core.py)
apps/api/tests/         pytest, incl. schema validation
cv/strikelens_cv/{ingest,segments,rounds,track,pose,strikes,overlay}/
cv/notebooks/  cv/configs/  cv/tests/
shared/schema/          tag, fight, fighter JSON Schemas
docs/                   all docs; decisions/ holds ADRs
data/  models/          local only, gitignored
```

## Commands

Tagger (`cd apps/tagger`):

```bash
npm install
npm run dev            # http://localhost:5173
npm run lint           # ESLint, zero warnings allowed
npm run format:check   # Prettier
npm run typecheck
npm test               # Vitest
npm run build
```

API (`cd apps/api`):

```bash
uv sync
uv run uvicorn app.main:app --reload   # http://localhost:8000/health
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

CV (`cd cv`):

```bash
uv sync                      # add --extra ingest / detect / pose / train when needed
uv run strikelens-cv --version
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

Whole repo: `uvx pre-commit run --all-files`.

CI (`.github/workflows/ci.yml`) runs jobs `tagger`, `api`, `cv` on every push and PR.

## Conventions

- TypeScript strict mode, `noUncheckedIndexedAccess`. No `any`, no non-null `!`.
- Python: type hints on every function. Ruff for lint and format, line length 100.
- Small pure functions. Keep I/O (files, DB, HTTP, video) at the edges.
- Stats return `None` (Python) or `null` (TS) when a value is undefined, such as
  accuracy with zero attempts. Never return 0 for "undefined".
- Field names match the JSON Schemas exactly (snake_case), in both TS and Python.
- Tests sit next to the code (tagger) or in `tests/` (Python).
- Docs: plain, direct English. Short sentences. No emoji.
- When a decision has trade-offs, write an ADR in `docs/decisions/` from `0000-template.md`.

## Feature loop

1. Pick one issue from the **Ready** column of the StrikeLens Roadmap project. Move it to **In progress**.
2. Create the branch `feat/<number>-<short-name>`.
3. Plan mode first: read the issue, the relevant docs, and the code. Propose a plan.
4. After approval, build it with tests.
5. Run lint and all tests for every part touched.
6. Open a PR that references the issue (`Closes #N`) and move it to **In review**.
7. After merge, move it to **Done**, update `CHANGELOG.md`, and `/clear` before the next issue.

Details: `docs/working-with-claude-code.md`.

## Where things live

- Product scope and non-goals: `docs/vision.md`
- Components and data flow: `docs/architecture.md`
- Fight rules (UCC Kickstriking, which Byon uses): `docs/rules.md`
- Strike taxonomy and hotkeys: `docs/tag-schema.md`
- Stat formulas and open questions: `docs/stat-definitions.md`
- What may and may not touch git: `docs/data-policy.md`
- Phases, gates, dates: `docs/roadmap.md`
- Local setup: `docs/dev-setup.md`
- Freefly context and questions: `docs/freefly-collab.md`
- Decisions: `docs/decisions/`
