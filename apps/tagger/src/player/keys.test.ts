import { playerKeyAction } from './keys'

const press = (key: string, target: EventTarget | null = document.body, mods = {}) =>
  playerKeyAction({
    key,
    ctrlKey: false,
    metaKey: false,
    altKey: false,
    shiftKey: false,
    target,
    ...mods,
  })

describe('playerKeyAction', () => {
  it('maps Space and the arrow keys', () => {
    expect(press(' ')).toBe('toggle-play')
    expect(press('ArrowLeft')).toBe('step-back')
    expect(press('ArrowRight')).toBe('step-forward')
  })

  it('ignores other keys', () => {
    expect(press('k')).toBeNull()
    expect(press('Enter')).toBeNull()
  })

  it('ignores keys with modifiers', () => {
    expect(press('ArrowLeft', document.body, { metaKey: true })).toBeNull()
    expect(press(' ', document.body, { ctrlKey: true })).toBeNull()
  })

  it('jumps 5 s with Shift and 30 s with Alt (Option on macOS)', () => {
    expect(press('ArrowLeft', document.body, { shiftKey: true })).toEqual({ jump: -5 })
    expect(press('ArrowRight', document.body, { shiftKey: true })).toEqual({ jump: 5 })
    expect(press('ArrowLeft', document.body, { altKey: true })).toEqual({ jump: -30 })
    expect(press('ArrowRight', document.body, { altKey: true })).toEqual({ jump: 30 })
  })

  it('ignores Shift+Alt arrows and Alt with other keys', () => {
    expect(press('ArrowRight', document.body, { altKey: true, shiftKey: true })).toBeNull()
    expect(press('j', document.body, { altKey: true })).toBeNull()
  })

  it('still plays with Shift held, and leaves Shift+letters to tagging', () => {
    expect(press(' ', document.body, { shiftKey: true })).toBe('toggle-play')
    expect(press('J', document.body, { shiftKey: true })).toBeNull()
  })

  it('ignores jumps typed into a form control', () => {
    expect(press('ArrowLeft', document.createElement('input'), { shiftKey: true })).toBeNull()
  })

  it.each(['input', 'textarea', 'select'])('ignores keys typed into a %s', (tag) => {
    expect(press(' ', document.createElement(tag))).toBeNull()
  })

  it('ignores keys typed into a contenteditable element', () => {
    const div = document.createElement('div')
    div.contentEditable = 'true'
    // jsdom does not compute isContentEditable from the attribute
    Object.defineProperty(div, 'isContentEditable', { value: true })
    expect(press(' ', div)).toBeNull()
  })

  it('handles keys while a button has focus', () => {
    expect(press(' ', document.createElement('button'))).toBe('toggle-play')
  })
})
