import type { Corner, Outcome, Tag, Target, Weapon } from '../api/types'
import { isFormControl } from '../player/keys'
import type { HotkeyAction } from './hotkeys'

/** How far before a suggestion the video starts, so the strike is seen coming. */
export const LEAD_MS = 1000

export type ReviewKey = 'next' | 'previous' | 'confirm' | 'reject'

/** What the analyst has set on the current suggestion before confirming it. */
export interface ReviewEdits {
  fighter?: Corner
  weapon?: Weapon
  outcome?: Outcome
  target?: Target
}

interface KeyInput {
  key: string
  ctrlKey: boolean
  metaKey: boolean
  altKey: boolean
  shiftKey: boolean
  target: EventTarget | null
}

/** Map a key to a review action, or null. Tab, Shift+Tab, Enter, and X (docs/tag-schema.md). */
export function reviewKeyAction(event: KeyInput): ReviewKey | null {
  if (event.ctrlKey || event.metaKey || event.altKey) return null
  if (isFormControl(event.target)) return null
  if (event.key === 'Tab') return event.shiftKey ? 'previous' : 'next'
  if (event.shiftKey) return null
  if (event.key === 'Enter') return 'confirm'
  if (event.key.toLowerCase() === 'x') return 'reject'
  return null
}

const isSuggestion = (tag: Tag) => tag.source === 'cv'

/** Pending CV suggestions at or above the confidence filter, in video order. */
export function pendingSuggestions(tags: readonly Tag[], minConfidence: number): Tag[] {
  return tags
    .filter((t) => isSuggestion(t) && t.status === 'pending')
    .filter((t) => (t.confidence ?? 0) >= minConfidence)
    .sort((a, b) => a.timestamp_ms - b.timestamp_ms || a.id.localeCompare(b.id))
}

/** How many CV suggestions above the filter have been confirmed or rejected. */
export function reviewProgress(
  tags: readonly Tag[],
  minConfidence: number,
): { reviewed: number; total: number } {
  const inFilter = tags.filter((t) => isSuggestion(t) && (t.confidence ?? 0) >= minConfidence)
  return {
    reviewed: inFilter.filter((t) => t.status !== 'pending').length,
    total: inFilter.length,
  }
}

/**
 * The suggestion to move to: the next (or previous) pending one by video time from
 * `fromMs`. Wraps around at the ends. Null when none is pending.
 */
export function stepSuggestion(
  pending: readonly Tag[],
  fromMs: number,
  direction: 1 | -1,
  currentId: string | null = null,
): Tag | null {
  const others = pending.filter((t) => t.id !== currentId)
  if (others.length === 0) return null
  if (direction === 1) return others.find((t) => t.timestamp_ms > fromMs) ?? others[0] ?? null
  return (
    [...others].reverse().find((t) => t.timestamp_ms < fromMs) ?? others[others.length - 1] ?? null
  )
}

/** Apply a tagging key to the current suggestion's edits. Esc clears them. */
export function editSuggestion(edits: ReviewEdits, action: HotkeyAction): ReviewEdits {
  if (action.field === 'clear') return {}
  return { ...edits, [action.field]: action.value }
}

/** The suggestion as it would be confirmed: its own values with the edits on top. */
export function withEdits(tag: Tag, edits: ReviewEdits): Tag {
  return { ...tag, ...edits }
}

export type ConfirmPlan =
  | { ok: true; patch: Required<ReviewEdits> & { status: 'confirmed' } }
  | { ok: false; error: string }

/**
 * The PATCH that confirms a suggestion. A confirmed tag needs a weapon, an outcome,
 * and a target (tag.schema.json), so missing ones are named. The tag keeps
 * `source: cv` and its confidence: only these fields change.
 */
export function planConfirm(tag: Tag, edits: ReviewEdits): ConfirmPlan {
  const merged = withEdits(tag, edits)
  const missing = (['weapon', 'outcome', 'target'] as const).filter((f) => merged[f] === null)
  if (missing.length > 0) {
    return { ok: false, error: `Set the ${missing.join(' and ')} first, then press Enter.` }
  }
  const { fighter, weapon, outcome, target } = merged
  if (weapon === null || outcome === null || target === null) {
    return { ok: false, error: 'Set the weapon, outcome, and target first.' }
  }
  return { ok: true, patch: { fighter, weapon, outcome, target, status: 'confirmed' } }
}
