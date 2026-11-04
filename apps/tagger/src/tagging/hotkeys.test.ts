import { actionFor, DEFAULT_HOTKEYS, hotkeyAction, keyFor } from './hotkeys'

const press = (key: string, target: EventTarget | null = document.body, mods = {}) =>
  hotkeyAction({ key, ctrlKey: false, metaKey: false, altKey: false, target, ...mods })

describe('hotkeyAction', () => {
  it('maps the default keys from tag-schema.md', () => {
    expect(press('q')).toEqual({ field: 'fighter', value: 'red' })
    expect(press('w')).toEqual({ field: 'fighter', value: 'blue' })
    expect(press('k')).toEqual({ field: 'weapon', value: 'kick' })
    expect(press('b')).toEqual({ field: 'outcome', value: 'blocked' })
    expect(press('2')).toEqual({ field: 'target', value: 'body' })
    expect(press('Escape')).toEqual({ field: 'clear' })
  })

  it('ignores case, so Shift and Caps Lock still work', () => {
    expect(press('K')).toEqual({ field: 'weapon', value: 'kick' })
  })

  it('leaves player and unbound keys alone', () => {
    expect(press(' ')).toBeNull()
    expect(press('ArrowLeft')).toBeNull()
    expect(press('z')).toBeNull()
  })

  it('ignores keys with Ctrl, Cmd, or Alt', () => {
    expect(press('c', document.body, { metaKey: true })).toBeNull()
    expect(press('z', document.body, { ctrlKey: true })).toBeNull()
    expect(press('k', document.body, { altKey: true })).toBeNull()
  })

  it.each(['input', 'textarea', 'select'])('ignores keys typed into a %s', (tag) => {
    expect(press('k', document.createElement(tag))).toBeNull()
  })

  it('binds every weapon, outcome, and target once', () => {
    const values = Object.values(DEFAULT_HOTKEYS).flatMap((a) => ('value' in a ? [a.value] : []))
    expect(new Set(values).size).toBe(values.length)
    expect(values).toHaveLength(2 + 8 + 3 + 3)
  })
})

describe('keyFor', () => {
  it('finds the key for a value', () => {
    expect(keyFor('weapon', 'teep')).toBe('T')
    expect(keyFor('target', 'legs')).toBe('3')
    expect(keyFor('fighter', 'blue')).toBe('W')
  })
})

describe('actionFor', () => {
  it('returns the same action the key sends', () => {
    expect(actionFor('outcome', 'blocked')).toEqual(press('b'))
    expect(actionFor('fighter', 'red')).toEqual(press('q'))
  })

  it('returns null for an unbound value', () => {
    expect(actionFor('weapon', 'backfist')).toBeNull()
  })
})
