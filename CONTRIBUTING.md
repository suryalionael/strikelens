# Contributing to StrikeLens

Thanks for helping. StrikeLens is small and run by one person part time, so clear,
focused contributions help most.

## Before you start

- Read [docs/data-policy.md](docs/data-policy.md). Never commit footage, frames,
  keypoints, labels, or model weights.
- Read [docs/dev-setup.md](docs/dev-setup.md) to get everything running.
- Check the issue list. If your idea has no issue, open one first so we can agree on
  scope before you write code.

## Workflow

1. Pick an issue and comment that you are taking it.
2. Branch from `main`: `feat/<issue-number>-<short-name>` (for example
   `feat/6-video-player`). Use `fix/` for bugs and `docs/` for doc-only changes.
3. Keep one feature per branch.
4. Write tests. Stat logic lives in pure functions with unit tests, never in UI
   components.
5. Run lint and tests for every part you touched (commands in
   [docs/dev-setup.md](docs/dev-setup.md)).
6. Open a PR. Fill in the template and put `Closes #N` in the description.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(tagger): add frame stepping with arrow keys
fix(api): return 404 for unknown fight id
docs: explain landed-strike open question
chore(ci): cache uv dependencies
```

## Stat definitions

Do not invent counting rules. If a rule is not settled in
[docs/stat-definitions.md](docs/stat-definitions.md), add it there as an open
question instead of picking an answer in code.

## Pre-commit hooks

Optional but recommended:

```bash
uvx pre-commit install
```

The hooks run Ruff, Prettier, and a check that blocks files over 5 MB.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
