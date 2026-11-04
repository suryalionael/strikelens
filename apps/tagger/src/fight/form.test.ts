import { EMPTY_FORM, fightFormErrors, type FightFormValues } from './form'

const valid: FightFormValues = {
  event: 'Test Event 1',
  date: '2026-11-01',
  weight_class: '',
  scheduled_rounds: 3,
  red: { kind: 'existing', id: 'a' },
  blue: { kind: 'new', name: 'Blue Fighter' },
}

describe('fightFormErrors', () => {
  it('accepts a complete form', () => {
    expect(fightFormErrors(valid)).toEqual([])
  })

  it('lists everything missing from an empty form', () => {
    expect(fightFormErrors(EMPTY_FORM)).toEqual([
      'Event name is required',
      'Date is required',
      'Pick or add the red corner fighter',
      'Pick or add the blue corner fighter',
    ])
  })

  it('rejects a blank event and a blank new fighter name', () => {
    expect(fightFormErrors({ ...valid, event: '  ', blue: { kind: 'new', name: ' ' } })).toEqual([
      'Event name is required',
      'Blue fighter needs a name',
    ])
  })

  it.each([0, -1, 2.5, Number.NaN])('rejects %s scheduled rounds', (scheduled_rounds) => {
    expect(fightFormErrors({ ...valid, scheduled_rounds })).toEqual([
      'Scheduled rounds must be a whole number, 1 or more',
    ])
  })

  it('rejects the same fighter in both corners', () => {
    expect(fightFormErrors({ ...valid, blue: { kind: 'existing', id: 'a' } })).toEqual([
      'Red and blue must be different fighters',
    ])
  })
})
