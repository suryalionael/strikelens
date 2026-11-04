import type { Tag } from '../api/types'

/** A confirmed human tag for tests. */
export function makeTag(overrides: Partial<Tag> = {}): Tag {
  return {
    id: 't1',
    fight_id: 'fight-1',
    round: 1,
    timestamp_ms: 61_250,
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
