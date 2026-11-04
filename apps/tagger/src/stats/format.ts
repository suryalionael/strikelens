import type { Corner, FightStats, MixEntry, TargetEntry } from '../api/types'

// Display only. Every number here was calculated by the API; these functions
// format it or reshape it for a chart, and never derive a new stat.

/** Shown for any value the API returns as null (undefined, not zero). */
export const DASH = '—'

/** 0.327 -> "32.7%". Null -> dash. */
export function formatPercent(value: number | null): string {
  return value === null ? DASH : `${(value * 100).toFixed(1)}%`
}

/** 15.888 -> "15.9". Null -> dash. */
export function formatRate(value: number | null): string {
  return value === null ? DASH : value.toFixed(1)
}

/** 2_310 seconds -> "38:30". */
export function formatDuration(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds))
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`
}

export function roundLabel(round: { number: number; partial: boolean }): string {
  return round.partial ? `R${round.number} (partial)` : `R${round.number}`
}

export interface CornerRow<V> {
  label: string
  red: V
  blue: V
}

/** One row per round, red and blue side by side. */
export function perRoundRows(stats: FightStats): CornerRow<{
  attempts: number
  landed: number
  accuracy: number | null
  strikes_per_minute: number | null
}>[] {
  return stats.rounds.map((round) => {
    const pick = (corner: Corner) => {
      const split = stats.fighters[corner].by_round.find((r) => r.round === round.number)
      return {
        attempts: split?.attempts ?? 0,
        landed: split?.landed ?? 0,
        accuracy: split?.accuracy ?? null,
        strikes_per_minute: split?.strikes_per_minute ?? null,
      }
    }
    return { label: roundLabel(round), red: pick('red'), blue: pick('blue') }
  })
}

/** Weapon groups or single weapons, red and blue side by side, in API order. */
export function mixRows(stats: FightStats, by: 'weapon_groups' | 'weapons'): CornerRow<MixEntry>[] {
  const { red, blue } = stats.fighters
  return Object.keys(red[by]).map((key) => ({
    label: key,
    red: red[by][key] ?? { attempts: 0, landed: 0, share: null },
    blue: blue[by][key] ?? { attempts: 0, landed: 0, share: null },
  }))
}

/** Targets, red and blue side by side, on landed strikes or on all attempts. */
export function targetRows(
  stats: FightStats,
  basis: 'landed' | 'attempted',
): CornerRow<TargetEntry>[] {
  const field = basis === 'landed' ? 'targets_landed' : 'targets_attempted'
  const { red, blue } = stats.fighters
  return Object.keys(red[field]).map((key) => ({
    label: key,
    red: red[field][key] ?? { count: 0, share: null },
    blue: blue[field][key] ?? { count: 0, share: null },
  }))
}

/** Flatten rows for Recharts, which wants one object per category. */
export function chartData<V>(
  rows: CornerRow<V>[],
  value: (v: V) => number | null,
): { label: string; red: number | null; blue: number | null }[] {
  return rows.map((row) => ({ label: row.label, red: value(row.red), blue: value(row.blue) }))
}
