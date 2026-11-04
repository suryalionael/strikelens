export type PlayerKeyAction = 'toggle-play' | 'step-back' | 'step-forward'

interface KeyInput {
  key: string
  ctrlKey: boolean
  metaKey: boolean
  altKey: boolean
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
  if (event.ctrlKey || event.metaKey || event.altKey) return null
  if (isFormControl(event.target)) return null
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
