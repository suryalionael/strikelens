import type { Corner, Fight, FightStats } from '../api/types'
import { formatPercent, formatRate, mixRows, perRoundRows, targetRows } from '../stats/format'

/** Instagram portrait, 4:5. */
export const CARD_WIDTH = 1080
export const CARD_HEIGHT = 1350

/**
 * Provisional. The credit wording is to be agreed with Freefly in Phase 4
 * (docs/freefly-collab.md, "Can StrikeLens be credited on cards that use it?").
 * The analyst can change it before exporting.
 */
export const DEFAULT_CREDIT = 'Tagged with StrikeLens'

export const PROVISIONAL_NOTE = 'Provisional definitions, not yet confirmed with Freefly'

export interface Header {
  event: string
  date: string
  names: Record<Corner, string>
}

export interface HeadlineBody {
  kind: 'headline'
  rows: { label: string; red: string; blue: string }[]
}

export interface BarsBody {
  kind: 'bars'
  /** null leaves a gap and a dash, never a zero bar. */
  categories: { label: string; red: number | null; blue: number | null }[]
  valueLabel: (value: number | null) => string
  /** Top of the scale. Bars are drawn as a share of it. */
  max: number
}

export interface Card {
  title: string
  subtitle: string | null
  header: Header
  body: HeadlineBody | BarsBody
  credit: string
  index: number
  total: number
  fileName: string
}

export function slug(text: string): string {
  return (
    text
      .normalize('NFKD')
      // Drop the accent marks NFKD splits off, so "é" becomes "e", not "e-".
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '') || 'fight'
  )
}

const count = (value: number | null) => (value === null ? '—' : String(value))
const percent = (value: number | null) => formatPercent(value)

/** A scale top that leaves headroom and is never zero. */
export function scaleMax(values: (number | null)[]): number {
  const top = Math.max(0, ...values.map((v) => v ?? 0))
  return top === 0 ? 1 : top
}

/** Bar height in pixels for a value on a scale of `max` over `height` pixels. */
export function barHeight(value: number | null, max: number, height: number): number {
  if (value === null || max <= 0) return 0
  return Math.round((Math.min(value, max) / max) * height)
}

/**
 * The carousel: one card per view, same header and footer on each. Every number
 * comes from the stats endpoint; this only chooses what each card shows.
 */
export function buildCards(
  stats: FightStats,
  fight: Pick<Fight, 'event' | 'date'>,
  names: Record<Corner, string>,
  credit: string,
): Card[] {
  const header: Header = { event: fight.event, date: fight.date, names }
  const partial = stats.rounds.find((r) => r.partial)
  const bodies: { title: string; subtitle: string | null; key: string; body: Card['body'] }[] = [
    {
      title: 'Strike stats',
      subtitle: `${stats.rounds.length} ${stats.rounds.length === 1 ? 'round' : 'rounds'}${
        partial ? `, R${partial.number} partial` : ''
      }`,
      key: 'headline',
      body: {
        kind: 'headline',
        rows: [
          {
            label: 'Attempts',
            red: String(stats.fighters.red.totals.attempts),
            blue: String(stats.fighters.blue.totals.attempts),
          },
          {
            label: 'Landed',
            red: String(stats.fighters.red.totals.landed),
            blue: String(stats.fighters.blue.totals.landed),
          },
          {
            label: 'Accuracy',
            red: formatPercent(stats.fighters.red.totals.accuracy),
            blue: formatPercent(stats.fighters.blue.totals.accuracy),
          },
          {
            label: 'Strikes per minute',
            red: formatRate(stats.fighters.red.totals.strikes_per_minute),
            blue: formatRate(stats.fighters.blue.totals.strikes_per_minute),
          },
        ],
      },
    },
  ]

  if (stats.rounds.length > 0) {
    const rows = perRoundRows(stats)
    const categories = rows.map((r) => ({
      label: r.label,
      red: r.red.attempts,
      blue: r.blue.attempts,
    }))
    bodies.push({
      title: 'Attempts per round',
      subtitle: partial ? 'A partial round ended early' : null,
      key: 'rounds',
      body: {
        kind: 'bars',
        categories,
        valueLabel: count,
        max: scaleMax(categories.flatMap((c) => [c.red, c.blue])),
      },
    })
  }

  const weapons = mixRows(stats, 'weapon_groups').map((r) => ({
    label: r.label,
    red: r.red.attempts,
    blue: r.blue.attempts,
  }))
  bodies.push({
    title: 'Weapon mix',
    subtitle: 'Attempts by strike type',
    key: 'weapons',
    body: {
      kind: 'bars',
      categories: weapons,
      valueLabel: count,
      max: scaleMax(weapons.flatMap((c) => [c.red, c.blue])),
    },
  })

  bodies.push({
    title: 'Target distribution',
    subtitle: 'Share of landed strikes',
    key: 'targets',
    body: {
      kind: 'bars',
      categories: targetRows(stats, 'landed').map((r) => ({
        label: r.label,
        red: r.red.share,
        blue: r.blue.share,
      })),
      valueLabel: percent,
      max: 1,
    },
  })

  const base = `strikelens-${slug(fight.event)}-${fight.date}`
  return bodies.map((b, i) => ({
    title: b.title,
    subtitle: b.subtitle,
    header,
    body: b.body,
    credit,
    index: i + 1,
    total: bodies.length,
    fileName: `${base}-${i + 1}-${b.key}.png`,
  }))
}
