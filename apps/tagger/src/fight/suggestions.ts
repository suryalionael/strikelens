import type { Segment, SegmentKind } from '../api/types'
import { SEGMENT_KINDS } from './segments'

/** A likely segment from `strikelens-cv suggest`, for the analyst to accept or dismiss. */
export interface Suggestion extends Segment {
  reason: string
}

const isWholeMs = (value: unknown): value is number =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0

const isKind = (value: unknown): value is SegmentKind =>
  typeof value === 'string' && (SEGMENT_KINDS as readonly string[]).includes(value)

/**
 * Read segment-suggestions.json. Throws an Error with a readable message when the
 * file is not what the CV pipeline writes.
 */
export function parseSuggestions(text: string): Suggestion[] {
  let data: unknown
  try {
    data = JSON.parse(text)
  } catch {
    throw new Error('The file is not JSON. Pick segment-suggestions.json from the ingest output.')
  }
  const list =
    typeof data === 'object' && data !== null && 'suggestions' in data
      ? data.suggestions
      : undefined
  if (!Array.isArray(list)) {
    throw new Error('No "suggestions" list in the file. Is it segment-suggestions.json?')
  }
  return list.map((item: unknown, index) => {
    const entry = (typeof item === 'object' && item !== null ? item : {}) as Record<string, unknown>
    const { kind, start_ms, end_ms, reason } = entry
    if (!isKind(kind) || !isWholeMs(start_ms) || !isWholeMs(end_ms) || end_ms <= start_ms) {
      throw new Error(`Suggestion ${index + 1} is not a valid segment.`)
    }
    return { kind, start_ms, end_ms, reason: typeof reason === 'string' ? reason : '' }
  })
}
