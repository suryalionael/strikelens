import type { Corner, Outcome, Tag, Target, Weapon } from '../api/types'
import type { RoundDraft } from '../fight/rounds'
import { formatTime } from '../player/time'
import { roundAt } from './tags'

/** Fields an analyst can change on a saved tag. */
export interface TagEdit {
  fighter?: Corner
  weapon?: Weapon
  outcome?: Outcome
  target?: Target
  timestamp_ms?: number
}

/** What is sent to PATCH /fights/{id}/tags/{tag_id}. */
export type TagPatch = TagEdit & { round?: number }

export type PlanResult = { ok: true; patch: TagPatch } | { ok: false; error: string }

/**
 * Turn an edit into a patch. A new time also moves the tag to the round that time
 * falls in; a time outside every marked round is refused, like a new tag would be.
 */
export function planEdit(tag: Tag, edit: TagEdit, rounds: readonly RoundDraft[]): PlanResult {
  if (edit.timestamp_ms === undefined || edit.timestamp_ms === tag.timestamp_ms) {
    const { timestamp_ms: _unchanged, ...rest } = edit
    void _unchanged
    return { ok: true, patch: rest }
  }
  const round = roundAt(rounds, edit.timestamp_ms)
  if (round === null) {
    return {
      ok: false,
      error: `Not changed: ${formatTime(edit.timestamp_ms / 1000)} is outside every marked round.`,
    }
  }
  return { ok: true, patch: { ...edit, round } }
}

/** A patch that puts every editable field back to how it was in `before`. */
export function revertPatch(before: Tag): TagPatch & Pick<Tag, 'status'> {
  return {
    fighter: before.fighter,
    weapon: before.weapon ?? undefined,
    outcome: before.outcome ?? undefined,
    target: before.target ?? undefined,
    timestamp_ms: before.timestamp_ms,
    round: before.round,
    status: before.status,
  }
}
