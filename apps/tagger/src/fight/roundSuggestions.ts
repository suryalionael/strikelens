import type { Round } from '../api/types'

/** A likely round from `strikelens-cv rounds`, for the analyst to check and accept. */
export interface RoundSuggestion extends Round {
  /** The scoreboard went away well before the round's full time: a stoppage, or check it. */
  partial: boolean
  reason: string
}

const isWholeMs = (value: unknown): value is number =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0

/**
 * Read round-suggestions.json. Throws an Error with a readable message when the
 * file is not what the CV pipeline writes.
 */
export function parseRoundSuggestions(text: string): RoundSuggestion[] {
  let data: unknown
  try {
    data = JSON.parse(text)
  } catch {
    throw new Error('The file is not JSON. Pick round-suggestions.json from the ingest output.')
  }
  const list =
    typeof data === 'object' && data !== null && 'suggestions' in data
      ? data.suggestions
      : undefined
  if (!Array.isArray(list)) {
    throw new Error('No "suggestions" list in the file. Is it round-suggestions.json?')
  }
  let previousEnd = -1
  return list.map((item: unknown, index) => {
    const entry = (typeof item === 'object' && item !== null ? item : {}) as Record<string, unknown>
    const { number, start_ms, end_ms, partial, reason } = entry
    if (
      number !== index + 1 ||
      !isWholeMs(start_ms) ||
      !isWholeMs(end_ms) ||
      end_ms <= start_ms ||
      start_ms < previousEnd
    ) {
      throw new Error(`Suggestion ${index + 1} is not a valid round.`)
    }
    previousEnd = end_ms
    return {
      number,
      start_ms,
      end_ms,
      partial: partial === true,
      reason: typeof reason === 'string' ? reason : '',
    }
  })
}
