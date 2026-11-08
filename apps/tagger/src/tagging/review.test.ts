import type { Tag } from '../api/types'
import {
  editSuggestion,
  pendingSuggestions,
  planConfirm,
  reviewKeyAction,
  reviewProgress,
  stepSuggestion,
} from './review'

function cv(id: string, ms: number, confidence: number, extra: Partial<Tag> = {}): Tag {
  return {
    id,
    fight_id: 'fight-1',
    round: 1,
    timestamp_ms: ms,
    fighter: 'red',
    weapon: 'kick',
    outcome: null,
    target: null,
    source: 'cv',
    confidence,
    status: 'pending',
    created_by: 'strike-model 0.1',
    created_at: '2026-11-07T10:00:00Z',
    ...extra,
  }
}

const press = (key: string, mods: Partial<Record<'shiftKey' | 'ctrlKey', boolean>> = {}) =>
  reviewKeyAction({
    key,
    ctrlKey: false,
    metaKey: false,
    altKey: false,
    shiftKey: false,
    target: document.body,
    ...mods,
  })

describe('reviewKeyAction', () => {
  it('maps Tab, Shift+Tab, Enter, and X', () => {
    expect(press('Tab')).toBe('next')
    expect(press('Tab', { shiftKey: true })).toBe('previous')
    expect(press('Enter')).toBe('confirm')
    expect(press('x')).toBe('reject')
    expect(press('X')).toBe('reject')
  })

  it('leaves other keys and modified keys alone', () => {
    expect(press('k')).toBeNull()
    expect(press('Enter', { shiftKey: true })).toBeNull()
    expect(press('x', { ctrlKey: true })).toBeNull()
  })
})

describe('pendingSuggestions and reviewProgress', () => {
  const tags = [
    cv('b', 5000, 0.9),
    cv('a', 2000, 0.4),
    cv('c', 8000, 0.8, { status: 'confirmed', outcome: 'landed', target: 'body' }),
    cv('d', 9000, 0.7, { status: 'rejected' }),
    { ...cv('h', 3000, 0), source: 'human', confidence: null, status: 'confirmed' } as Tag,
  ]

  it('lists pending CV suggestions above the filter, in video order', () => {
    expect(pendingSuggestions(tags, 0).map((t) => t.id)).toEqual(['a', 'b'])
    expect(pendingSuggestions(tags, 0.5).map((t) => t.id)).toEqual(['b'])
  })

  it('counts reviewed suggestions above the filter', () => {
    expect(reviewProgress(tags, 0)).toEqual({ reviewed: 2, total: 4 })
    expect(reviewProgress(tags, 0.75)).toEqual({ reviewed: 1, total: 2 })
  })
})

describe('stepSuggestion', () => {
  const pending = [cv('a', 2000, 1), cv('b', 5000, 1), cv('c', 8000, 1)]

  it('goes to the next and previous by time, and wraps', () => {
    expect(stepSuggestion(pending, 3000, 1)?.id).toBe('b')
    expect(stepSuggestion(pending, 3000, -1)?.id).toBe('a')
    expect(stepSuggestion(pending, 9000, 1)?.id).toBe('a')
    expect(stepSuggestion(pending, 1000, -1)?.id).toBe('c')
  })

  it('skips the suggestion just reviewed, and stops when none is left', () => {
    expect(stepSuggestion(pending, 5000, 1, 'b')?.id).toBe('c')
    expect(stepSuggestion([pending[0] as Tag], 0, 1, 'a')).toBeNull()
  })
})

describe('editing and confirming a suggestion', () => {
  it('applies tagging keys, and Esc clears the edits', () => {
    const edited = editSuggestion({}, { field: 'outcome', value: 'landed' })
    expect(editSuggestion(edited, { field: 'weapon', value: 'knee' })).toEqual({
      outcome: 'landed',
      weapon: 'knee',
    })
    expect(editSuggestion(edited, { field: 'clear' })).toEqual({})
  })

  it('needs an outcome and a target before it confirms', () => {
    expect(planConfirm(cv('a', 0, 1), {})).toEqual({
      ok: false,
      error: 'Set the outcome and target first, then press Enter.',
    })
    expect(planConfirm(cv('a', 0, 1), { outcome: 'landed', target: 'head' })).toEqual({
      ok: true,
      patch: {
        fighter: 'red',
        weapon: 'kick',
        outcome: 'landed',
        target: 'head',
        status: 'confirmed',
      },
    })
  })

  it('keeps the analyst’s change of weapon and fighter', () => {
    const plan = planConfirm(cv('a', 0, 1), {
      weapon: 'teep',
      fighter: 'blue',
      outcome: 'missed',
      target: 'body',
    })
    expect(plan.ok && plan.patch).toMatchObject({ weapon: 'teep', fighter: 'blue' })
  })

  it('names a missing weapon too', () => {
    const plan = planConfirm(cv('a', 0, 1, { weapon: null }), { outcome: 'landed' })
    expect(plan).toEqual({ ok: false, error: 'Set the weapon and target first, then press Enter.' })
  })
})
