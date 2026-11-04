import type { Round } from '../api/types'

/** A round while it is being marked. `end_ms` is null until the analyst marks the end. */
export interface RoundDraft {
  number: number
  start_ms: number
  end_ms: number | null
}

export interface RoundError {
  round: number | null
  message: string
}

export type NextMark = { kind: 'start'; round: number } | { kind: 'end'; round: number } | null

function lastRound(rounds: readonly RoundDraft[]): RoundDraft | undefined {
  return rounds[rounds.length - 1]
}

/** What the main button should do next. Null once every scheduled round is marked. */
export function nextMark(rounds: readonly RoundDraft[], scheduled: number): NextMark {
  const last = lastRound(rounds)
  if (last && last.end_ms === null) return { kind: 'end', round: last.number }
  if (rounds.length >= scheduled) return null
  return { kind: 'start', round: rounds.length + 1 }
}

/** Start the next round at `ms`. Does nothing if the last round is still open. */
export function startRound(rounds: readonly RoundDraft[], ms: number): RoundDraft[] {
  if (lastRound(rounds)?.end_ms === null) return [...rounds]
  return [...rounds, { number: rounds.length + 1, start_ms: ms, end_ms: null }]
}

/** End the open round at `ms`. Does nothing if no round is open. */
export function endRound(rounds: readonly RoundDraft[], ms: number): RoundDraft[] {
  return rounds.map((r, i) =>
    i === rounds.length - 1 && r.end_ms === null ? { ...r, end_ms: ms } : r,
  )
}

export function setRoundTime(
  rounds: readonly RoundDraft[],
  number: number,
  field: 'start_ms' | 'end_ms',
  ms: number,
): RoundDraft[] {
  return rounds.map((r) => (r.number === number ? { ...r, [field]: ms } : r))
}

export function removeLastRound(rounds: readonly RoundDraft[]): RoundDraft[] {
  return rounds.slice(0, -1)
}

/** Problems that stop the rounds from being saved. Empty means valid. */
export function roundErrors(rounds: readonly RoundDraft[], scheduled: number): RoundError[] {
  const errors: RoundError[] = []
  if (rounds.length > scheduled) {
    errors.push({ round: null, message: `More rounds than scheduled (${scheduled})` })
  }
  rounds.forEach((r, i) => {
    if (r.end_ms !== null && r.end_ms <= r.start_ms) {
      errors.push({ round: r.number, message: `Round ${r.number} ends before it starts` })
    }
    const previous = rounds[i - 1]
    if (previous?.end_ms != null && r.start_ms < previous.end_ms) {
      errors.push({
        round: r.number,
        message: `Round ${r.number} starts before round ${previous.number} ends`,
      })
    }
  })
  return errors
}

/** Rounds with both marks, in the shape the API stores. The open round is left out. */
export function completedRounds(rounds: readonly RoundDraft[]): Round[] {
  return rounds.flatMap((r) =>
    r.end_ms === null ? [] : [{ number: r.number, start_ms: r.start_ms, end_ms: r.end_ms }],
  )
}
