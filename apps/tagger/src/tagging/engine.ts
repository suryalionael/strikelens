import type { Corner, Outcome, Target, Weapon } from '../api/types'
import type { HotkeyAction } from './hotkeys'

export interface Draft {
  /** Video time of the draft's first key, or null before any key. */
  started_ms: number | null
  weapon: Weapon | null
  outcome: Outcome | null
  target: Target | null
}

export interface TaggingState {
  /** Stays selected between tags. */
  fighter: Corner | null
  draft: Draft
}

export interface CompleteDraft {
  timestamp_ms: number
  fighter: Corner
  weapon: Weapon
  outcome: Outcome
  target: Target
}

export const EMPTY_DRAFT: Draft = { started_ms: null, weapon: null, outcome: null, target: null }
export const INITIAL_TAGGING: TaggingState = { fighter: null, draft: EMPTY_DRAFT }

/** True when a draft has been started but not yet completed. */
export function hasDraft(state: TaggingState): boolean {
  return state.draft.started_ms !== null
}

/**
 * Apply one key. Keys can come in any order and a repeated field is replaced.
 * When fighter, weapon, outcome, and target are all set, the draft is returned as
 * `complete` and a new empty draft starts, with the fighter kept.
 */
export function applyKey(
  state: TaggingState,
  action: HotkeyAction,
  now_ms: number,
): { state: TaggingState; complete: CompleteDraft | null } {
  if (action.field === 'clear') {
    return { state: { ...state, draft: EMPTY_DRAFT }, complete: null }
  }

  const started_ms = state.draft.started_ms ?? now_ms
  const fighter = action.field === 'fighter' ? action.value : state.fighter
  const draft: Draft =
    action.field === 'fighter'
      ? { ...state.draft, started_ms }
      : { ...state.draft, started_ms, [action.field]: action.value }

  const { weapon, outcome, target } = draft
  if (fighter && weapon && outcome && target) {
    return {
      state: { fighter, draft: EMPTY_DRAFT },
      complete: { timestamp_ms: started_ms, fighter, weapon, outcome, target },
    }
  }
  return { state: { fighter, draft }, complete: null }
}
