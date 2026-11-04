import type { RoundDraft } from '../fight/rounds'
import { makeTag } from '../test/tag'
import { planEdit, revertPatch } from './edits'

const ROUNDS: RoundDraft[] = [
  { number: 1, start_ms: 0, end_ms: 180_000 },
  { number: 2, start_ms: 240_000, end_ms: 420_000 },
]

describe('planEdit', () => {
  it('passes field changes through', () => {
    expect(planEdit(makeTag(), { weapon: 'jab', outcome: 'missed' }, ROUNDS)).toEqual({
      ok: true,
      patch: { weapon: 'jab', outcome: 'missed' },
    })
  })

  it('moves the tag to the round a new time falls in', () => {
    expect(planEdit(makeTag(), { timestamp_ms: 300_000 }, ROUNDS)).toEqual({
      ok: true,
      patch: { timestamp_ms: 300_000, round: 2 },
    })
  })

  it('refuses a time outside every marked round', () => {
    expect(planEdit(makeTag(), { timestamp_ms: 200_000 }, ROUNDS)).toEqual({
      ok: false,
      error: 'Not changed: 03:20.000 is outside every marked round.',
    })
  })

  it('ignores an unchanged time', () => {
    expect(planEdit(makeTag(), { timestamp_ms: 61_250, target: 'head' }, [])).toEqual({
      ok: true,
      patch: { target: 'head' },
    })
  })
})

describe('revertPatch', () => {
  it('puts every editable field back', () => {
    const before = makeTag({ fighter: 'blue', weapon: 'teep', timestamp_ms: 300_000, round: 2 })
    expect(revertPatch(before)).toEqual({
      fighter: 'blue',
      weapon: 'teep',
      outcome: 'landed',
      target: 'body',
      timestamp_ms: 300_000,
      round: 2,
      status: 'confirmed',
    })
  })
})
