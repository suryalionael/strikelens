# 0002. AGPL-3.0 licence

- **Status:** accepted
- **Date:** 2026-11-03

## Context

The CV pipeline uses Ultralytics YOLO for fighter detection. Ultralytics is
licensed AGPL-3.0, with a paid enterprise licence as the alternative. AGPL requires
that software using it, including software offered over a network, is released
under AGPL with its source available.

The project is meant to be public, free, and usable by Freefly and others.

## Decision

License all of StrikeLens under AGPL-3.0. The repo is public.

## Consequences

- We can use Ultralytics without a paid licence.
- Anyone who runs a modified StrikeLens as a web service must publish their changes.
  That fits the goal of an open tool.
- Some companies avoid AGPL code. That limits commercial reuse, which is acceptable
  for v1.
- If we later want a more permissive licence, we must first replace YOLO with a
  permissively licensed detector (for example, an Apache-2.0 model) and get
  agreement from all contributors.
- The licence covers code and docs only. Footage and labels are never in the repo
  (see [data-policy.md](../data-policy.md)).
