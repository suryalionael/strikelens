import {
  completedRounds,
  endRound,
  nextMark,
  removeLastRound,
  roundErrors,
  setRoundTime,
  startRound,
  type RoundDraft,
} from './rounds'

const closed = (number: number, start_ms: number, end_ms: number): RoundDraft => ({
  number,
  start_ms,
  end_ms,
})

describe('marking rounds', () => {
  it('alternates start and end, numbering rounds from 1', () => {
    let rounds: RoundDraft[] = []
    expect(nextMark(rounds, 3)).toEqual({ kind: 'start', round: 1 })
    rounds = startRound(rounds, 1000)
    expect(nextMark(rounds, 3)).toEqual({ kind: 'end', round: 1 })
    rounds = endRound(rounds, 181000)
    expect(nextMark(rounds, 3)).toEqual({ kind: 'start', round: 2 })
    rounds = startRound(rounds, 241000)
    expect(rounds).toEqual([closed(1, 1000, 181000), { number: 2, start_ms: 241000, end_ms: null }])
  })

  it('is done once every scheduled round has both marks', () => {
    expect(nextMark([closed(1, 0, 10), closed(2, 20, 30)], 2)).toBeNull()
  })

  it('does not start a round while one is open', () => {
    const open = startRound([], 1000)
    expect(startRound(open, 5000)).toEqual(open)
  })

  it('does not end a round when none is open', () => {
    const rounds = [closed(1, 0, 10)]
    expect(endRound(rounds, 50)).toEqual(rounds)
  })

  it('edits one time of one round', () => {
    const rounds = [closed(1, 0, 10), closed(2, 20, 30)]
    expect(setRoundTime(rounds, 2, 'end_ms', 35)).toEqual([closed(1, 0, 10), closed(2, 20, 35)])
  })

  it('removes the last round', () => {
    expect(removeLastRound([closed(1, 0, 10), closed(2, 20, 30)])).toEqual([closed(1, 0, 10)])
  })

  it('saves only rounds with both marks', () => {
    const rounds = startRound([closed(1, 0, 10)], 20)
    expect(completedRounds(rounds)).toEqual([{ number: 1, start_ms: 0, end_ms: 10 }])
  })
})

describe('roundErrors', () => {
  it('accepts valid rounds, including a fight that ended early', () => {
    expect(roundErrors([closed(1, 0, 180000), closed(2, 240000, 300500)], 3)).toEqual([])
  })

  it('accepts an open round', () => {
    expect(roundErrors(startRound([closed(1, 0, 10)], 20), 3)).toEqual([])
  })

  it('rejects a round that ends before or when it starts', () => {
    expect(roundErrors([closed(1, 100, 50)], 3)).toEqual([
      { round: 1, message: 'Round 1 ends before it starts' },
    ])
    expect(roundErrors([closed(1, 100, 100)], 3)).toHaveLength(1)
  })

  it('rejects overlapping rounds', () => {
    expect(roundErrors([closed(1, 0, 100), closed(2, 90, 200)], 3)).toEqual([
      { round: 2, message: 'Round 2 starts before round 1 ends' },
    ])
  })

  it('allows a round to start exactly when the previous one ends', () => {
    expect(roundErrors([closed(1, 0, 100), closed(2, 100, 200)], 3)).toEqual([])
  })

  it('rejects more rounds than scheduled', () => {
    expect(roundErrors([closed(1, 0, 10), closed(2, 20, 30)], 1)).toEqual([
      { round: null, message: 'More rounds than scheduled (1)' },
    ])
  })
})
