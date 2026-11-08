export type PlayerKeyAction = 'toggle-play' | 'step-back' | 'step-forward' | { jump: number } // seconds, negative is back

/** Shift+arrow jumps a short way, Alt+arrow (Option on macOS) a long way. */
export const JUMP_SECONDS = { short: 5, long: 30 } as const

interface KeyInput {
  key: string
  ctrlKey: boolean
  metaKey: boolean
  altKey: boolean
  shiftKey: boolean
  target: EventTarget | null
}

// Form controls own these keys: Space types a space, arrows move the caret or
// change a select's value.
export function isFormControl(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  if (target.isContentEditable) return true
  return ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)
}

/** Map a key press to a player action, or null if the player should ignore it. */
export function playerKeyAction(event: KeyInput): PlayerKeyAction | null {
  if (event.ctrlKey || event.metaKey) return null
  if (isFormControl(event.target)) return null
  const arrow = event.key === 'ArrowLeft' ? -1 : event.key === 'ArrowRight' ? 1 : 0
  if (event.altKey && event.shiftKey) return null
  if (event.altKey) return arrow ? { jump: arrow * JUMP_SECONDS.long } : null
  if (event.shiftKey && arrow) return { jump: arrow * JUMP_SECONDS.short }
  switch (event.key) {
    case ' ':
      return 'toggle-play'
    case 'ArrowLeft':
      return 'step-back'
    case 'ArrowRight':
      return 'step-forward'
    default:
      return null
  }
}
