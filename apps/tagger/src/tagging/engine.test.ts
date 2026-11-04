import type { Corner, Outcome, Target, Weapon } from '../api/types'
import { applyKey, EMPTY_DRAFT, hasDraft, INITIAL_TAGGING, type TaggingState } from './engine'
import type { HotkeyAction } from './hotkeys'

const fighter = (value: Corner): HotkeyAction => ({ field: 'fighter', value })
const weapon = (value: Weapon): HotkeyAction => ({ field: 'weapon', value })
const outcome = (value: Outcome): HotkeyAction => ({ field: 'outcome', value })
const target = (value: Target): HotkeyAction => ({ field: 'target', value })
const clear: HotkeyAction = { field: 'clear' }

/** Press keys at the given video times and collect completed tags. */
function press(keys: [HotkeyAction, number][], start: TaggingState = INITIAL_TAGGING) {
  let state = start
  const completed = []
  for (const [action, ms] of keys) {
    const result = applyKey(state, action, ms)
    state = result.state
    if (result.complete) completed.push(result.complete)
  }
  return { state, completed }
}

describe('applyKey', () => {
  it('completes Q K L 2 at the time of the first key', () => {
    const { state, completed } = press([
      [fighter('red'), 1000],
      [weapon('kick'), 1100],
      [outcome('landed'), 1200],
      [target('body'), 1300],
    ])
    expect(completed).toEqual([
      { timestamp_ms: 1000, fighter: 'red', weapon: 'kick', outcome: 'landed', target: 'body' },
    ])
    expect(state).toEqual({ fighter: 'red', draft: EMPTY_DRAFT })
  })

  it('keeps the fighter, so the next tag needs three keys', () => {
    const first = press([
      [fighter('blue'), 0],
      [weapon('jab'), 0],
      [outcome('missed'), 0],
      [target('head'), 0],
    ])
    const { completed } = press(
      [
        [weapon('teep'), 5000],
        [outcome('blocked'), 5100],
        [target('body'), 5200],
      ],
      first.state,
    )
    expect(completed).toEqual([
      { timestamp_ms: 5000, fighter: 'blue', weapon: 'teep', outcome: 'blocked', target: 'body' },
    ])
  })

  it('accepts keys in any order', () => {
    const { completed } = press([
      [target('legs'), 200],
      [outcome('landed'), 300],
      [fighter('red'), 400],
      [weapon('kick'), 500],
    ])
    expect(completed[0]).toMatchObject({ timestamp_ms: 200, target: 'legs', weapon: 'kick' })
  })

  it('replaces a field pressed twice', () => {
    const { completed } = press([
      [fighter('red'), 0],
      [weapon('jab'), 0],
      [weapon('cross'), 0],
      [outcome('landed'), 0],
      [target('head'), 0],
    ])
    expect(completed[0]?.weapon).toBe('cross')
  })

  it('switching fighter mid-draft changes the fighter but not the time', () => {
    const { completed } = press([
      [fighter('red'), 0],
      [weapon('hook'), 100],
      [outcome('landed'), 0],
      [target('head'), 0],
      [weapon('hook'), 900],
      [fighter('blue'), 950],
      [outcome('missed'), 1000],
      [target('head'), 1100],
    ])
    expect(completed[1]).toMatchObject({ timestamp_ms: 900, fighter: 'blue' })
  })

  it('waits for a fighter before completing', () => {
    const { state, completed } = press([
      [weapon('kick'), 0],
      [outcome('landed'), 0],
      [target('body'), 0],
    ])
    expect(completed).toEqual([])
    expect(hasDraft(state)).toBe(true)
  })

  it('clears the draft with Esc but keeps the fighter', () => {
    const { state } = press([
      [fighter('red'), 0],
      [weapon('kick'), 100],
      [clear, 200],
    ])
    expect(state).toEqual({ fighter: 'red', draft: EMPTY_DRAFT })
    expect(hasDraft(state)).toBe(false)
  })

  it('starts the clock again after Esc', () => {
    const { completed } = press([
      [fighter('red'), 0],
      [weapon('kick'), 100],
      [clear, 200],
      [weapon('knee'), 3000],
      [outcome('landed'), 3100],
      [target('body'), 3200],
    ])
    expect(completed[0]).toMatchObject({ timestamp_ms: 3000, weapon: 'knee' })
  })
})
