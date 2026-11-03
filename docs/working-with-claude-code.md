# Working with Claude Code

StrikeLens is built one issue at a time, with Claude Code as a pair programmer.
This page describes the loop so every session starts and ends the same way.

`CLAUDE.md` at the repo root is read at the start of every session. It holds the
hard rules, commands, and conventions. Keep it short and current.

## The feature loop

1. **Pick one issue.** Take it from the **Ready** column of the StrikeLens Roadmap
   project. Move it to **In progress**.
2. **Branch.** `git switch -c feat/<number>-<short-name>`, for example
   `feat/6-video-player`. Use `fix/` for bugs and `docs/` for doc-only work.
3. **Plan first.** Start Claude Code in plan mode (Shift+Tab). Ask it to read the
   issue (`gh issue view <number>`), the docs the issue links to, and the code it
   touches. It proposes a plan. Push back until the plan is right.
4. **Build with tests.** After you approve the plan, Claude Code builds it. Stat
   logic goes in pure functions with tests first.
5. **Check.** Run lint and all tests for every part touched (commands in
   [dev-setup.md](dev-setup.md)). Fix everything. No "it works on my machine".
6. **Open a PR.** Title in Conventional Commits form. Description includes
   `Closes #<number>` and how it was tested. Move the issue to **In review**.
7. **After merge.** Move the issue to **Done**, add a line to `CHANGELOG.md` under
   `Unreleased`, pull `main`, and run `/clear` before starting the next issue.

## Starting prompt

A good first message in a new session:

```
Work on issue #<number>. Read it with gh, read the docs it links to and CLAUDE.md,
then look at the relevant code. Propose a plan. Do not write code yet.
```

## Rules for sessions

- One issue per session. If you find other work, open an issue for it instead.
- Do not let Claude Code change stat definitions. If a rule is unclear, add an open
  question to [stat-definitions.md](stat-definitions.md) and ask Freefly.
- Never paste footage, frames, or Freefly's private data into a session.
- If a decision has real trade-offs, ask for an ADR in `docs/decisions/`.
- Review every diff before committing. You own the code.

## Moving issues on the board

From the command line (project number from `gh project list --owner suryalionael`):

```bash
gh project item-list <project-number> --owner suryalionael
```

Changing Status is easier on the board itself: drag the card between columns.

## Keeping docs current

When a PR changes behaviour, update the doc in the same PR:

| Change | Doc |
|---|---|
| New or changed hotkey, tag field | `tag-schema.md` and `shared/schema/` |
| New or changed stat | `stat-definitions.md` |
| New component or data flow | `architecture.md` |
| New command or dependency | `dev-setup.md` and `CLAUDE.md` |
| A decision with trade-offs | new ADR |
