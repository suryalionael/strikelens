import type { Corner, Outcome, Target, Weapon } from '../api/types'
import { isFormControl } from '../player/keys'

export type HotkeyAction =
  | { field: 'fighter'; value: Corner }
  | { field: 'weapon'; value: Weapon }
  | { field: 'outcome'; value: Outcome }
  | { field: 'target'; value: Target }
  | { field: 'clear' }

export type Hotkeys = Readonly<Record<string, HotkeyAction>>

/**
 * Default bindings from docs/tag-schema.md. Letter keys are lower case; matching
 * ignores case. Fighter keys: ADR 0005. Space and the arrows belong to the player.
 */
export const DEFAULT_HOTKEYS: Hotkeys = {
  q: { field: 'fighter', value: 'red' },
  w: { field: 'fighter', value: 'blue' },
  j: { field: 'weapon', value: 'jab' },
  c: { field: 'weapon', value: 'cross' },
  h: { field: 'weapon', value: 'hook' },
  u: { field: 'weapon', value: 'uppercut' },
  k: { field: 'weapon', value: 'kick' },
  n: { field: 'weapon', value: 'knee' },
  e: { field: 'weapon', value: 'elbow' },
  t: { field: 'weapon', value: 'teep' },
  l: { field: 'outcome', value: 'landed' },
  m: { field: 'outcome', value: 'missed' },
  b: { field: 'outcome', value: 'blocked' },
  '1': { field: 'target', value: 'head' },
  '2': { field: 'target', value: 'body' },
  '3': { field: 'target', value: 'legs' },
  escape: { field: 'clear' },
}

interface KeyInput {
  key: string
  ctrlKey: boolean
  metaKey: boolean
  altKey: boolean
  target: EventTarget | null
}

/** Map a key press to a tagging action, or null if tagging should ignore it. */
export function hotkeyAction(event: KeyInput, hotkeys: Hotkeys = DEFAULT_HOTKEYS) {
  if (event.ctrlKey || event.metaKey || event.altKey) return null
  if (isFormControl(event.target)) return null
  return hotkeys[event.key.toLowerCase()] ?? null
}

type ValueField = Exclude<HotkeyAction['field'], 'clear'>

function binding(field: ValueField, value: string, hotkeys: Hotkeys) {
  return Object.entries(hotkeys).find(
    ([, action]) => action.field === field && 'value' in action && action.value === value,
  )
}

/** The key bound to a field value, for on-screen hints. */
export function keyFor(
  field: ValueField,
  value: string,
  hotkeys: Hotkeys = DEFAULT_HOTKEYS,
): string | null {
  return binding(field, value, hotkeys)?.[0].toUpperCase() ?? null
}

/** The action a key for this field value would send. Clicks use it, so they match keys. */
export function actionFor(
  field: ValueField,
  value: string,
  hotkeys: Hotkeys = DEFAULT_HOTKEYS,
): HotkeyAction | null {
  return binding(field, value, hotkeys)?.[1] ?? null
}
