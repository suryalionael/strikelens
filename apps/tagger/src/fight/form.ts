export type FighterChoice = { kind: 'existing'; id: string } | { kind: 'new'; name: string }

export interface FightFormValues {
  event: string
  date: string
  weight_class: string
  scheduled_rounds: number
  red: FighterChoice | null
  blue: FighterChoice | null
}

export const EMPTY_FORM: FightFormValues = {
  event: '',
  date: '',
  weight_class: '',
  scheduled_rounds: 3,
  red: null,
  blue: null,
}

function cornerError(corner: 'Red' | 'Blue', choice: FighterChoice | null): string | null {
  if (choice === null) return `Pick or add the ${corner.toLowerCase()} corner fighter`
  if (choice.kind === 'new' && choice.name.trim() === '') return `${corner} fighter needs a name`
  return null
}

/** Problems that stop the form from being submitted. Empty means valid. */
export function fightFormErrors(form: FightFormValues): string[] {
  const errors: string[] = []
  if (form.event.trim() === '') errors.push('Event name is required')
  if (!/^\d{4}-\d{2}-\d{2}$/.test(form.date)) errors.push('Date is required')
  if (!Number.isInteger(form.scheduled_rounds) || form.scheduled_rounds < 1) {
    errors.push('Scheduled rounds must be a whole number, 1 or more')
  }
  for (const error of [cornerError('Red', form.red), cornerError('Blue', form.blue)]) {
    if (error) errors.push(error)
  }
  const { red, blue } = form
  if (red?.kind === 'existing' && blue?.kind === 'existing' && red.id === blue.id) {
    errors.push('Red and blue must be different fighters')
  }
  return errors
}
