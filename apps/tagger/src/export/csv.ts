import type { Corner, FightStats, Tag } from '../api/types'

type Cell = string | number | null

/**
 * One CSV cell (RFC 4180). Null is an empty cell, never 0. Text that a spreadsheet
 * would run as a formula (=, +, -, @) gets a leading apostrophe.
 */
export function csvCell(value: Cell): string {
  if (value === null) return ''
  if (typeof value === 'number') return String(value)
  const safe = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value
  return /[",\r\n]/.test(safe) ? `"${safe.replaceAll('"', '""')}"` : safe
}

export function toCsv(header: readonly string[], rows: readonly Cell[][]): string {
  return [header, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n') + '\r\n'
}

/** Columns in the order of shared/schema/tag.schema.json. */
export const TAG_COLUMNS = [
  'id',
  'fight_id',
  'round',
  'timestamp_ms',
  'fighter',
  'weapon',
  'outcome',
  'target',
  'source',
  'confidence',
  'status',
  'created_by',
  'created_at',
] as const satisfies readonly (keyof Tag)[]

/** Every confirmed tag, in video order. Pending and rejected tags are left out. */
export function tagsCsv(tags: readonly Tag[]): string {
  const rows = tags
    .filter((t) => t.status === 'confirmed')
    .sort((a, b) => a.timestamp_ms - b.timestamp_ms)
    .map((t) => TAG_COLUMNS.map((col) => t[col]))
  return toCsv(TAG_COLUMNS, rows)
}

export const STATS_COLUMNS = ['group', 'item', 'fighter', 'metric', 'value'] as const

const CORNERS: Corner[] = ['red', 'blue']

/**
 * The stats summary in long format (one value per row), so it pivots cleanly in a
 * spreadsheet. Values are copied from the API as they are; nothing is recalculated.
 */
export function statsCsv(stats: FightStats): string {
  const rows: Cell[][] = [
    ['fight', 'all', 'both', 'fight_time_s', stats.fight_time_s],
    ['fight', 'all', 'both', 'uncounted_tags', stats.uncounted_tags],
  ]
  for (const round of stats.rounds) {
    rows.push(['round', String(round.number), 'both', 'time_s', round.time_s])
    rows.push(['round', String(round.number), 'both', 'partial', round.partial ? 1 : 0])
  }
  for (const corner of CORNERS) {
    const f = stats.fighters[corner]
    const split = (group: string, item: string, s: typeof f.totals) => {
      rows.push([group, item, corner, 'attempts', s.attempts])
      rows.push([group, item, corner, 'landed', s.landed])
      rows.push([group, item, corner, 'accuracy', s.accuracy])
      rows.push([group, item, corner, 'strikes_per_minute', s.strikes_per_minute])
    }
    split('totals', 'all', f.totals)
    for (const r of f.by_round) split('round', String(r.round), r)
    for (const [group, mix] of [
      ['weapon', f.weapons],
      ['weapon_group', f.weapon_groups],
    ] as const) {
      for (const [item, entry] of Object.entries(mix)) {
        rows.push([group, item, corner, 'attempts', entry.attempts])
        rows.push([group, item, corner, 'landed', entry.landed])
        rows.push([group, item, corner, 'share', entry.share])
      }
    }
    for (const [group, dist] of [
      ['target_landed', f.targets_landed],
      ['target_attempted', f.targets_attempted],
    ] as const) {
      for (const [item, entry] of Object.entries(dist)) {
        rows.push([group, item, corner, 'count', entry.count])
        rows.push([group, item, corner, 'share', entry.share])
      }
    }
  }
  for (const rule of stats.provisional_rules) rows.push(['provisional_rule', '', '', 'rule', rule])
  return toCsv(STATS_COLUMNS, rows)
}
