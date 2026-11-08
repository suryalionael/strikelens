import { parseRoundSuggestions } from './roundSuggestions'

const file = (suggestions: unknown) => JSON.stringify({ suggestions })

describe('parseRoundSuggestions', () => {
  it('reads the rounds the CV pipeline suggests', () => {
    const text = file([
      { number: 1, start_ms: 179_000, end_ms: 359_000, partial: false, reason: 'Scoreboard' },
      { number: 2, start_ms: 425_000, end_ms: 487_000, partial: true, reason: 'Stoppage?' },
    ])
    expect(parseRoundSuggestions(text)).toEqual([
      { number: 1, start_ms: 179_000, end_ms: 359_000, partial: false, reason: 'Scoreboard' },
      { number: 2, start_ms: 425_000, end_ms: 487_000, partial: true, reason: 'Stoppage?' },
    ])
  })

  it('accepts a file with no rounds found', () => {
    expect(parseRoundSuggestions(file([]))).toEqual([])
  })

  it.each([
    ['not JSON', 'not json', /not JSON/],
    ['another file', '{"shots": []}', /No "suggestions" list/],
    ['a number out of order', file([{ number: 2, start_ms: 0, end_ms: 1000 }]), /Suggestion 1/],
    [
      'an end before the start',
      file([{ number: 1, start_ms: 5000, end_ms: 1000 }]),
      /Suggestion 1/,
    ],
    [
      'overlapping rounds',
      file([
        { number: 1, start_ms: 0, end_ms: 5000 },
        { number: 2, start_ms: 4000, end_ms: 9000 },
      ]),
      /Suggestion 2/,
    ],
  ])('rejects %s', (_name, text, message) => {
    expect(() => parseRoundSuggestions(text)).toThrow(message)
  })
})
