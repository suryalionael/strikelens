import { parseSuggestions } from './suggestions'

const file = (suggestions: unknown) => JSON.stringify({ strikelens_cv: '0.0.1', suggestions })

describe('parseSuggestions', () => {
  it('reads what strikelens-cv writes', () => {
    const replay = { kind: 'replay', start_ms: 60_000, end_ms: 63_000, reason: '3 short shots' }
    expect(parseSuggestions(file([replay]))).toEqual([replay])
  })

  it('allows a missing reason', () => {
    expect(parseSuggestions(file([{ kind: 'non_fight', start_ms: 0, end_ms: 5 }]))).toEqual([
      { kind: 'non_fight', start_ms: 0, end_ms: 5, reason: '' },
    ])
  })

  it('says when the file is not JSON or not a suggestions file', () => {
    expect(() => parseSuggestions('frames')).toThrow('not JSON')
    expect(() => parseSuggestions(JSON.stringify({ shots: [] }))).toThrow('No "suggestions"')
  })

  it.each([
    { kind: 'slow_motion', start_ms: 0, end_ms: 5 },
    { kind: 'replay', start_ms: 5, end_ms: 5 },
    { kind: 'replay', start_ms: -1, end_ms: 5 },
    { kind: 'replay', start_ms: 0.5, end_ms: 5 },
    'replay',
  ])('rejects a bad suggestion: %j', (bad) => {
    expect(() => parseSuggestions(file([bad]))).toThrow('Suggestion 1 is not a valid segment.')
  })
})
