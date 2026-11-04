import type { Tag } from '../api/types'
import type { RoundDraft } from '../fight/rounds'
import { markers, position, roundBands, timeAt, timelineRange } from './timelineLayout'

const ROUNDS: RoundDraft[] = [
  { number: 1, start_ms: 100_000, end_ms: 280_000 },
  { number: 2, start_ms: 340_000, end_ms: 500_000 },
]

function tag(overrides: Partial<Tag> = {}): Tag {
  return {
    id: 't1',
    fight_id: 'f1',
    round: 1,
    timestamp_ms: 190_000,
    fighter: 'red',
    weapon: 'kick',
    outcome: 'landed',
    target: 'body',
    source: 'human',
    confidence: null,
    status: 'confirmed',
    created_by: 'analyst',
    created_at: '2026-11-04T10:00:00Z',
    ...overrides,
  }
}

describe('timelineRange', () => {
  it('spans the marked rounds with a little padding', () => {
    expect(timelineRange(ROUNDS, 3_600_000, 0)).toEqual({ start_ms: 92_000, end_ms: 508_000 })
  })

  it('shows the whole video before any round is marked', () => {
    expect(timelineRange([], 600_000, 0)).toEqual({ start_ms: 0, end_ms: 600_000 })
  })

  it('stretches an open round to the playhead', () => {
    const open: RoundDraft[] = [{ number: 1, start_ms: 0, end_ms: null }]
    expect(timelineRange(open, 600_000, 50_000).end_ms).toBe(51_000)
  })

  it('never returns an empty range', () => {
    const range = timelineRange([{ number: 1, start_ms: 5_000, end_ms: null }], 0, 0)
    expect(range.end_ms).toBeGreaterThan(range.start_ms)
    expect(timelineRange([], 0, 0).end_ms).toBe(1)
  })
})

describe('position and timeAt', () => {
  const range = { start_ms: 1_000, end_ms: 11_000 }

  it('maps times to percent and back', () => {
    expect(position(1_000, range)).toBe(0)
    expect(position(6_000, range)).toBe(50)
    expect(position(11_000, range)).toBe(100)
    expect(timeAt(50, range)).toBe(6_000)
  })

  it('clamps times outside the range', () => {
    expect(position(0, range)).toBe(0)
    expect(position(20_000, range)).toBe(100)
    expect(timeAt(150, range)).toBe(11_000)
  })

  it('handles a zero-length range', () => {
    expect(position(5, { start_ms: 5, end_ms: 5 })).toBe(0)
  })
})

describe('roundBands', () => {
  it('places each round as a band, leaving breaks empty', () => {
    const range = { start_ms: 0, end_ms: 500_000 }
    const bands = roundBands(ROUNDS, range, 0)
    expect(bands[0]).toMatchObject({ number: 1, left: 20, open: false })
    expect(bands[0]?.width).toBeCloseTo(36)
    expect(bands[1]?.left).toBe(68)
  })

  it('marks an open round', () => {
    const bands = roundBands(
      [{ number: 1, start_ms: 0, end_ms: null }],
      { start_ms: 0, end_ms: 100 },
      50,
    )
    expect(bands[0]).toEqual({ number: 1, left: 0, width: 50, open: true })
  })
})

describe('markers', () => {
  const range = { start_ms: 100_000, end_ms: 500_000 }

  it('puts each confirmed tag on its fighter lane with a shape for its outcome', () => {
    const result = markers(
      [
        tag(),
        tag({ id: 't2', fighter: 'blue', outcome: 'missed', timestamp_ms: 300_000 }),
        tag({ id: 't3', outcome: 'blocked' }),
      ],
      range,
    )
    expect(result.map((m) => [m.id, m.fighter, m.shape])).toEqual([
      ['t1', 'red', 'filled'],
      ['t2', 'blue', 'ring'],
      ['t3', 'red', 'square'],
    ])
    expect(result[0]?.left).toBe(22.5)
    expect(result[0]?.label).toBe('Red kick landed body at 03:10.000, round 1')
  })

  it('leaves out pending and rejected tags', () => {
    const result = markers(
      [tag({ status: 'pending', id: 'p' }), tag({ status: 'rejected', id: 'r' }), tag()],
      range,
    )
    expect(result.map((m) => m.id)).toEqual(['t1'])
  })

  it('handles a whole fight of tags quickly', () => {
    const many = Array.from({ length: 2_000 }, (_, i) =>
      tag({ id: `t${i}`, timestamp_ms: 100_000 + i * 150, fighter: i % 2 ? 'blue' : 'red' }),
    )
    const started = performance.now()
    expect(markers(many, range)).toHaveLength(2_000)
    expect(performance.now() - started).toBeLessThan(100)
  })
})
