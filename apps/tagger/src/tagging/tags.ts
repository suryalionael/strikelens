import type { TagInput } from '../api/types'
import type { RoundDraft } from '../fight/rounds'
import { formatTime } from '../player/time'
import type { CompleteDraft } from './engine'

/**
 * The round a video time falls in, or null if it is outside every marked round.
 * An open round (start marked, end not yet) covers everything after its start.
 * At a shared boundary the later round wins.
 */
export function roundAt(rounds: readonly RoundDraft[], ms: number): number | null {
  for (let i = rounds.length - 1; i >= 0; i--) {
    const r = rounds[i]
    if (r && ms >= r.start_ms && (r.end_ms === null || ms <= r.end_ms)) return r.number
  }
  return null
}

export type BuildResult = { ok: true; tag: TagInput } | { ok: false; error: string }

/** Turn a finished draft into a confirmed human tag for the API. */
export function buildTag(
  draft: CompleteDraft,
  rounds: readonly RoundDraft[],
  created_by: string,
): BuildResult {
  const round = roundAt(rounds, draft.timestamp_ms)
  if (round === null) {
    return {
      ok: false,
      error: `Not saved: ${formatTime(draft.timestamp_ms / 1000)} is outside every marked round.`,
    }
  }
  return {
    ok: true,
    tag: {
      round,
      timestamp_ms: draft.timestamp_ms,
      fighter: draft.fighter,
      weapon: draft.weapon,
      outcome: draft.outcome,
      target: draft.target,
      source: 'human',
      confidence: null,
      status: 'confirmed',
      created_by,
    },
  }
}
