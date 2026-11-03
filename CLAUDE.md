# StrikeLens

Human-in-the-loop fight analytics for kickboxing. Full version of this file is
written in the docs stage.

## Hard rules

1. Never commit footage, frames, keypoints, labels, or model weights.
2. Never invent stat definitions. Unsettled rules are open questions for Freefly.
3. Stat calculations are pure functions with unit tests. No stat logic in UI.
4. Human tags and CV suggestions share one schema in `shared/schema/`.
5. Run lint and tests before saying a task is done.
6. One feature per branch: `feat/<issue-number>-<short-name>`. Conventional Commits. PRs say `Closes #N`.
7. Keep it free to run. No paid services.
