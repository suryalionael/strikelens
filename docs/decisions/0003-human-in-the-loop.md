# 0003. Human in the loop for every counted strike

- **Status:** accepted
- **Date:** 2026-11-03

## Context

Freefly publishes stats under their own name. A wrong number damages their
credibility. Automatic strike detection from broadcast video is unreliable today:
fighters overlap, cameras cut, replays repeat moments, and "landed" is a judgement
call even for people.

We also have no labelled Byon data to train on yet.

## Decision

Every strike that counts toward a stat is confirmed by a person. The CV model only
**suggests**. Suggestions are stored as tags with `source: "cv"`, a `confidence`,
and `status: "pending"`. Only `confirmed` tags count. Human tags and suggestions
share one schema.

Landed vs missed and target are tagged by the analyst in v1, with no CV suggestion.

## Consequences

- Stats are as trustworthy as Freefly's own counting, and faster to produce.
- The tagger must work well with no CV at all. That is Phase 1, and it is useful on
  its own.
- Every confirmed and rejected suggestion becomes labelled training data for free.
- We can measure the model honestly (precision, recall, timing error) against
  confirmed tags (issue #28).
- Speed gains depend on the analyst trusting and quickly reviewing suggestions.
  Review UX (issue #26) matters as much as model accuracy.
- Moving a stat to "mostly automatic" later is a new decision with its own ADR and
  evaluation.
