import { playerKeyAction } from './keys'

const press = (key: string, target: EventTarget | null = document.body, mods = {}) =>
  playerKeyAction({ key, ctrlKey: false, metaKey: false, altKey: false, target, ...mods })

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
    expect(press('ArrowRight', document.body, { altKey: true })).toBeNull()
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
