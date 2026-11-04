import Ajv2020 from 'ajv/dist/2020'
import addFormats from 'ajv-formats'
import tagSchema from '../../../../shared/schema/tag.schema.json'
import type { RoundDraft } from '../fight/rounds'
import type { CompleteDraft } from './engine'
import { buildTag, roundAt } from './tags'

const rounds: RoundDraft[] = [
  { number: 1, start_ms: 1000, end_ms: 181000 },
  { number: 2, start_ms: 241000, end_ms: 421000 },
]

const draft: CompleteDraft = {
  timestamp_ms: 61250,
  fighter: 'red',
  weapon: 'kick',
  outcome: 'landed',
  target: 'body',
}

describe('roundAt', () => {
  it.each([
    [1000, 1],
    [61250, 1],
    [181000, 1],
    [241000, 2],
    [421000, 2],
  ])('puts %i ms in round %i', (ms, round) => {
    expect(roundAt(rounds, ms)).toBe(round)
  })

  it.each([0, 999, 200000, 500000])('puts %i ms outside every round', (ms) => {
    expect(roundAt(rounds, ms)).toBeNull()
  })

  it('treats an open round as running until it is ended', () => {
    const open: RoundDraft[] = [...rounds, { number: 3, start_ms: 481000, end_ms: null }]
    expect(roundAt(open, 9_999_999)).toBe(3)
  })

  it('gives a shared boundary to the later round', () => {
    const backToBack: RoundDraft[] = [
      { number: 1, start_ms: 0, end_ms: 100 },
      { number: 2, start_ms: 100, end_ms: 200 },
    ]
    expect(roundAt(backToBack, 100)).toBe(2)
  })
})

describe('buildTag', () => {
  it('builds a confirmed human tag in the right round', () => {
    expect(buildTag(draft, rounds, 'analyst')).toEqual({
      ok: true,
      tag: {
        round: 1,
        timestamp_ms: 61250,
        fighter: 'red',
        weapon: 'kick',
        outcome: 'landed',
        target: 'body',
        source: 'human',
        confidence: null,
        status: 'confirmed',
        created_by: 'analyst',
      },
    })
  })

  it('refuses a tag outside every round and says why', () => {
    expect(buildTag({ ...draft, timestamp_ms: 200000 }, rounds, 'analyst')).toEqual({
      ok: false,
      error: 'Not saved: 03:20.000 is outside every marked round.',
    })
  })

  it('produces tags that match tag.schema.json once the API adds its fields', () => {
    const ajv = new Ajv2020({ strict: false })
    addFormats(ajv)
    const validate = ajv.compile(tagSchema)
    const result = buildTag(draft, rounds, 'analyst')
    if (!result.ok) throw new Error(result.error)
    const saved = {
      ...result.tag,
      id: '3f1c2b8e-8a4d-4a7e-9a51-0c1d2e3f4a5b',
      fight_id: '9b2e7c10-1d3f-4b6a-8c9d-0e1f2a3b4c5d',
      created_at: '2026-11-04T10:15:00Z',
    }
    expect(validate(saved), JSON.stringify(validate.errors)).toBe(true)
  })
})
