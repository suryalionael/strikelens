# Dev setup

How to run every part of StrikeLens locally.

## Requirements

| Tool | Version | Check |
|---|---|---|
| Node.js | 20 or newer (CI uses 22) | `node -v` |
| npm | comes with Node | `npm -v` |
| Python | 3.11 or newer (CI uses 3.12) | `python3 --version` |
| uv | any recent | `uv --version` |
| Git | any recent | `git --version` |
| FFmpeg | needed from Phase 2 | `ffmpeg -version` |

Install uv with `pip install uv` or `brew install uv`. uv downloads the right
Python version if yours is too old.

## Clone

```bash
git clone https://github.com/suryalionael/strikelens.git
cd strikelens
```

## Tagger (`apps/tagger`)

```bash
cd apps/tagger
npm install
npm run dev            # http://localhost:5173
```

Checks:

```bash
npm run lint           # ESLint, fails on any warning
npm run format:check   # Prettier (npm run format to fix)
npm run typecheck      # tsc
npm test               # Vitest, once
npm run test:watch     # Vitest, watch mode
npm run build          # production build into dist/
```

## API (`apps/api`)

```bash
cd apps/api
uv sync                                  # creates .venv and installs deps
uv run uvicorn app.main:app --reload     # http://localhost:8000
```

Open http://localhost:8000/health (should return `{"status":"ok"}`) and
http://localhost:8000/docs for the interactive API docs.

Checks:

```bash
uv run ruff check .          # lint (add --fix to fix)
uv run ruff format --check . # format (drop --check to fix)
uv run pytest
```

## CV pipeline (`cv`)

```bash
cd cv
uv sync
uv run strikelens-cv --version
```

The base install has no heavy dependencies. Add extras only when you work on that stage:

```bash
uv sync --extra ingest    # OpenCV, PySceneDetect
uv sync --extra detect    # Ultralytics YOLO
uv sync --extra pose      # MediaPipe
uv sync --extra train     # PyTorch
```

You can combine them: `uv sync --extra ingest --extra detect`.

RTMPose (MMPose) is not an extra. See `cv/README.md` and
[ADR 0004](decisions/0004-pose-library.md).

Checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Pre-commit hooks

Run all hooks over the repo:

```bash
uvx pre-commit run --all-files
```

Install them so they run on every commit:

```bash
uvx pre-commit install
```

Hooks: end-of-file fixer, trailing whitespace, YAML and JSON checks, a 5 MB file
size limit, Ruff (lint and format), and Prettier for the tagger.

## Data folders

Put local videos in `data/raw/`. Everything under `data/` and `models/` is
gitignored. Read [data-policy.md](data-policy.md) first.

## CI

`.github/workflows/ci.yml` runs on every push to `main` and every PR. It has three
jobs, matching the commands above:

- `tagger`: `npm ci`, lint, format check, typecheck, test, build
- `api`: `uv sync --locked`, Ruff, pytest
- `cv`: `uv sync --locked`, Ruff, pytest

If you add a Python dependency, commit the updated `uv.lock`. If you add an npm
dependency, commit the updated `package-lock.json`. CI fails otherwise.

## Troubleshooting

- **`uv sync --locked` fails in CI:** run `uv lock` locally and commit `uv.lock`.
- **Port 5173 or 8000 in use:** `npm run dev -- --port 5174` or
  `uv run uvicorn app.main:app --reload --port 8001`.
- **Prettier fails in CI:** run `npm run format` in `apps/tagger` and commit.
