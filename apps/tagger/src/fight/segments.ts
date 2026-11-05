import type { Segment, SegmentKind } from '../api/types'
import { formatTime } from '../player/time'

/** A segment while it is being marked. `end_ms` is null until the analyst marks the end. */
export interface SegmentDraft {
  kind: SegmentKind
  start_ms: number
  end_ms: number | null
}

export const SEGMENT_KINDS: readonly SegmentKind[] = ['replay', 'non_fight']

export const SEGMENT_LABEL: Record<SegmentKind, string> = {
  replay: 'Replay',
  non_fight: 'Non-fight',
}

const byStart = (a: { start_ms: number }, b: { start_ms: number }) => a.start_ms - b.start_ms

export function openSegment(segments: readonly SegmentDraft[]): SegmentDraft | undefined {
  return segments.find((s) => s.end_ms === null)
}

/** Start a segment at `ms`. Does nothing while another segment is open. */
export function startSegment(
  segments: readonly SegmentDraft[],
  kind: SegmentKind,
  ms: number,
): SegmentDraft[] {
  if (openSegment(segments)) return [...segments]
  return [...segments, { kind, start_ms: ms, end_ms: null }].sort(byStart)
}

/** End the open segment at `ms`. Does nothing if none is open. */
export function endSegment(segments: readonly SegmentDraft[], ms: number): SegmentDraft[] {
  return segments.map((s) => (s.end_ms === null ? { ...s, end_ms: ms } : s))
}

/** Add a finished segment, for example an accepted suggestion. */
export function addSegment(segments: readonly SegmentDraft[], segment: Segment): SegmentDraft[] {
  return [...segments, { ...segment }].sort(byStart)
}

export function setSegmentTime(
  segments: readonly SegmentDraft[],
  index: number,
  field: 'start_ms' | 'end_ms',
  ms: number,
): SegmentDraft[] {
  return segments.map((s, i) => (i === index ? { ...s, [field]: ms } : s)).sort(byStart)
}

export function removeSegment(segments: readonly SegmentDraft[], index: number): SegmentDraft[] {
  return segments.filter((_, i) => i !== index)
}

const name = (s: SegmentDraft) => `${SEGMENT_LABEL[s.kind]} at ${formatTime(s.start_ms / 1000)}`

/** Problems that stop the segments from being saved. Empty means valid. */
export function segmentErrors(segments: readonly SegmentDraft[]): string[] {
  const errors: string[] = []
  const sorted = [...segments].sort(byStart)
  sorted.forEach((s, i) => {
    if (s.end_ms !== null && s.end_ms <= s.start_ms) {
      errors.push(`${name(s)} ends before it starts`)
    }
    const previous = sorted[i - 1]
    // An open segment runs on with the video, so anything after it overlaps.
    if (previous && (previous.end_ms === null || s.start_ms < previous.end_ms)) {
      errors.push(`${name(s)} overlaps ${name(previous).toLowerCase()}`)
    }
  })
  return errors
}

/** Segments with both marks, sorted, in the shape the API stores. */
export function completedSegments(segments: readonly SegmentDraft[]): Segment[] {
  return segments
    .flatMap((s) =>
      s.end_ms === null ? [] : [{ kind: s.kind, start_ms: s.start_ms, end_ms: s.end_ms }],
    )
    .sort(byStart)
}

/**
 * The segment a time falls in, or undefined. The end is exclusive, like the API's
 * stats. An open segment covers everything from its start on.
 */
export function segmentAt(segments: readonly SegmentDraft[], ms: number): SegmentDraft | undefined {
  return segments.find((s) => s.start_ms <= ms && (s.end_ms === null || ms < s.end_ms))
}
