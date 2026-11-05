import type { FighterStats, FightStats } from '../api/types'

const groups = (punch: number, kick: number) => ({
  punch: { attempts: punch, landed: 0, share: punch + kick ? punch / (punch + kick) : null },
  kick: { attempts: kick, landed: 0, share: punch + kick ? kick / (punch + kick) : null },
  knee: { attempts: 0, landed: 0, share: punch + kick ? 0 : null },
  elbow: { attempts: 0, landed: 0, share: punch + kick ? 0 : null },
})

function fighter(overrides: Partial<FighterStats> = {}): FighterStats {
  return {
    totals: { attempts: 3, landed: 2, accuracy: 2 / 3, strikes_per_minute: 0.5 },
    by_round: [
      { round: 1, attempts: 2, landed: 1, accuracy: 0.5, strikes_per_minute: 2 / 3 },
      { round: 2, attempts: 1, landed: 1, accuracy: 1, strikes_per_minute: 1 / 3 },
    ],
    weapons: {
      jab: { attempts: 2, landed: 1, share: 2 / 3 },
      kick: { attempts: 1, landed: 1, share: 1 / 3 },
    },
    weapon_groups: groups(2, 1),
    targets_landed: {
      head: { count: 1, share: 0.5 },
      body: { count: 1, share: 0.5 },
      legs: { count: 0, share: 0 },
    },
    targets_attempted: {
      head: { count: 2, share: 2 / 3 },
      body: { count: 1, share: 1 / 3 },
      legs: { count: 0, share: 0 },
    },
    ...overrides,
  }
}

/** A small fight: red has tags, blue has none, round 2 is partial. */
export function sampleStats(overrides: Partial<FightStats> = {}): FightStats {
  return {
    fight_id: 'fight-1',
    fight_time_s: 360,
    rounds: [
      { number: 1, start_ms: 0, end_ms: 180_000, time_s: 180, partial: false },
      { number: 2, start_ms: 240_000, end_ms: 420_000, time_s: 180, partial: true },
    ],
    fighters: {
      red: fighter(),
      blue: fighter({
        totals: { attempts: 0, landed: 0, accuracy: null, strikes_per_minute: 0 },
        by_round: [
          { round: 1, attempts: 0, landed: 0, accuracy: null, strikes_per_minute: 0 },
          { round: 2, attempts: 0, landed: 0, accuracy: null, strikes_per_minute: 0 },
        ],
        weapons: {
          jab: { attempts: 0, landed: 0, share: null },
          kick: { attempts: 0, landed: 0, share: null },
        },
        weapon_groups: groups(0, 0),
        targets_landed: {
          head: { count: 0, share: null },
          body: { count: 0, share: null },
          legs: { count: 0, share: null },
        },
        targets_attempted: {
          head: { count: 0, share: null },
          body: { count: 0, share: null },
          legs: { count: 0, share: null },
        },
      }),
    },
    uncounted_tags: 0,
    segment_tags: 0,
    provisional_rules: ['Every strike in a combination is its own attempt.'],
    ...overrides,
  }
}
