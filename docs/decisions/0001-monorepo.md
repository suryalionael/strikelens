# 0001. One repo for tagger, API, CV, and schemas

- **Status:** accepted
- **Date:** 2026-11-03

## Context

StrikeLens has three parts in two languages: a React tagger, a FastAPI service,
and a Python CV pipeline. All three read and write the same tag shape. One person
builds it part time, and most features touch more than one part (for example,
suggestion review touches the CV output, the API, and the tagger).

## Decision

Keep everything in one repository: `apps/tagger`, `apps/api`, `cv`, and
`shared/schema`. Each part keeps its own package manager and lockfile (npm for
the tagger, uv for the API and CV). No monorepo build tool.

## Consequences

- One PR can change the schema and every consumer together, so they never drift.
- One issue tracker, one board, one CI file.
- CI runs three separate jobs, so a tagger change still runs the Python jobs. Fine
  at this size. Path filters can be added later if CI gets slow.
- The API and CV are separate Python projects. They cannot import each other. Shared
  logic goes through the JSON Schemas, or gets its own package later if needed.
