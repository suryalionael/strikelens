import type { Corner, Outcome, Tag } from '../api/types'
import type { RoundDraft } from '../fight/rounds'
import { formatTime } from '../player/time'

export interface TimeRange {
  start_ms: number
  end_ms: number
}

/** Space on each side of the rounds, as a share of their total span. */
const PAD = 0.02

/**
 * The part of the video the timeline shows. With rounds marked, it spans the first
 * round start to the last round end, so a long broadcast file does not squash the
 * fight into a sliver. An open round runs to the latest of its start, the playhead,
 * and its last tag. With no rounds, it is the whole video.
 */
export function timelineRange(
  rounds: readonly RoundDraft[],
  duration_ms: number,
  latest_ms: number,
): TimeRange {
  const first = rounds[0]
  if (!first) return { start_ms: 0, end_ms: Math.max(duration_ms, latest_ms, 1) }
  const start = first.start_ms
  const ends = rounds.map((r) => r.end_ms ?? Math.max(r.start_ms, latest_ms))
  const end = Math.max(...ends, start + 1)
  const pad = (end - start) * PAD
  return { start_ms: Math.max(0, start - pad), end_ms: end + pad }
}

/** Position of a time along the range, from 0 to 100 (percent). Clamped. */
export function position(ms: number, range: TimeRange): number {
  const span = range.end_ms - range.start_ms
  if (span <= 0) return 0
  return Math.min(100, Math.max(0, ((ms - range.start_ms) / span) * 100))
}

/** Time at a position (0 to 100) along the range. Used when the track is clicked. */
export function timeAt(percent: number, range: TimeRange): number {
  const p = Math.min(100, Math.max(0, percent))
  return Math.round(range.start_ms + (p / 100) * (range.end_ms - range.start_ms))
}

export interface RoundBand {
  number: number
  left: number
  width: number
  open: boolean
}

export function roundBands(
  rounds: readonly RoundDraft[],
  range: TimeRange,
  latest_ms: number,
): RoundBand[] {
  return rounds.map((r) => {
    const end = r.end_ms ?? Math.max(r.start_ms, latest_ms)
    const left = position(r.start_ms, range)
    return { number: r.number, left, width: position(end, range) - left, open: r.end_ms === null }
  })
}

export type MarkerShape = 'filled' | 'ring' | 'square'

/** Outcome is shown by shape, so it does not depend on colour. Fighter is the lane. */
export const OUTCOME_SHAPE: Record<Outcome, MarkerShape> = {
  landed: 'filled',
  missed: 'ring',
  blocked: 'square',
}

export interface Marker {
  id: string
  fighter: Corner
  left: number
  shape: MarkerShape
  label: string
  timestamp_ms: number
}

/** One marker per confirmed tag, positioned on its fighter's lane. */
export function markers(tags: readonly Tag[], range: TimeRange): Marker[] {
  return tags
    .filter((t) => t.status === 'confirmed')
    .map((t) => ({
      id: t.id,
      fighter: t.fighter,
      left: position(t.timestamp_ms, range),
      shape: t.outcome ? OUTCOME_SHAPE[t.outcome] : 'ring',
      label: `${t.fighter === 'red' ? 'Red' : 'Blue'} ${[t.weapon, t.outcome, t.target].join(' ')} at ${formatTime(t.timestamp_ms / 1000)}, round ${t.round}`,
      timestamp_ms: t.timestamp_ms,
    }))
}
