import type { Tag } from '../api/types'

/** A tag change that can be undone. Each one keeps the full tag(s) it needs. */
export type TagAction =
  | { kind: 'create'; tag: Tag }
  | { kind: 'edit'; before: Tag; after: Tag }
  | { kind: 'delete'; tag: Tag }

/** The issue asks for at least 20 steps; older steps are dropped past this. */
export const HISTORY_LIMIT = 50

export function record(history: readonly TagAction[], action: TagAction): TagAction[] {
  return [...history, action].slice(-HISTORY_LIMIT)
}

/** What undoing an action does to the server. */
export type UndoStep =
  { op: 'delete'; tag: Tag } | { op: 'restore'; tag: Tag } | { op: 'revert'; to: Tag }

export function undoStep(action: TagAction): UndoStep {
  switch (action.kind) {
    case 'create':
      return { op: 'delete', tag: action.tag }
    case 'delete':
      return { op: 'restore', tag: action.tag }
    case 'edit':
      return { op: 'revert', to: action.before }
  }
}

/** The tag list after a tag was saved: replaced if it is there, added if not. */
export function upsert(tags: readonly Tag[], tag: Tag): Tag[] {
  return tags.some((t) => t.id === tag.id)
    ? tags.map((t) => (t.id === tag.id ? tag : t))
    : [...tags, tag]
}

export function without(tags: readonly Tag[], id: string): Tag[] {
  return tags.filter((t) => t.id !== id)
}
