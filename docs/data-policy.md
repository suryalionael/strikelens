# Data policy

StrikeLens is a public repo. The data it works on is not ours. This page says
what may go in git, what may not, and why.

## Who owns what

| Data | Owner | Our right to use it |
|---|---|---|
| Byon Combat fight footage | Byon Combat | None by default. Local analysis only, unless Byon gives written permission |
| Freefly's published stats | Freefly Metrics | Public figures, cited with credit (for example the test fixture) |
| Freefly's raw tags and spreadsheets | Freefly Metrics | Only what they share, only for the purpose they agree to |
| Tags made in StrikeLens on Byon footage | Shared question (to agree with Freefly) | Local only until agreed |
| Public practice clips (issue #3) | Their uploaders | Local practice only |
| Code, schemas, docs | This project | AGPL-3.0 |

## Never in git

- Video files (`*.mp4`, `*.mov`, `*.mkv`, and any other format)
- Extracted frames or screenshots from fights
- Keypoints, tracks, or detections from fights
- Tags, labels, or training windows from real fights
- Model weights (`*.pt`, `*.onnx`, checkpoints)
- SQLite databases with real data
- Notebook outputs that show frames or real data
- `.env` files and any keys

## How this is enforced

1. `.gitignore` ignores everything under `data/` and `models/` except their
   `README.md` and `.gitkeep` files, and ignores video and weight extensions anywhere.
2. The pre-commit hook `check-added-large-files` blocks any file over 5 MB.
3. The PR template asks you to confirm no data is committed.
4. Code review. If in doubt, leave it out.

If something slips through, do not just delete it in a new commit: it stays in
history. Report it (see [SECURITY.md](../SECURITY.md)) so it can be removed from
history.

## What is safe to commit

- Synthetic data you made up for tests (for example, a list of fake tags). Mark it
  as synthetic in the file or test name.
- Freefly's **published** aggregate figures, with credit, as in
  `apps/api/tests/test_stats_core.py`.
- Configs, schemas, and code.
- Screenshots of the StrikeLens UI that do not show fight footage, or that use
  footage we have written permission to show.

## Sharing data between machines

Use a private channel: a private Google Drive folder, a USB drive, or Freefly's own
storage. Never a public link. Never git LFS on this repo.

For Colab and Kaggle training, upload data to a **private** dataset or a private
Drive folder. Kaggle datasets are public by default: check the setting.

## Consent and people

- Fighters are public figures in a public sport, but stats about them are still
  about real people. Present numbers neutrally. No rankings or claims beyond what
  the counted data shows.
- Analyst usernames in `created_by` are for audit only. Do not publish them without
  consent.

## Demo material (Gate 2 overlay video)

The overlay demo uses real footage. Before sharing it outside the team:

1. Ask Freefly whether they are comfortable with it.
2. Ask Byon (directly or through Freefly) for permission to show their footage, or
   use a clip that is clearly fair use (short, transformed, credited). If in doubt,
   show it privately only.

## Open items

- Who owns tags made in StrikeLens on Byon footage, and can any of them become a
  public dataset? To agree with Freefly (see [freefly-collab.md](freefly-collab.md)).
- Whether Byon will grant permission for footage use in demos.
