import { sampleStats } from '../test/fightStats'
import { barHeight, buildCards, CARD_HEIGHT, CARD_WIDTH, scaleMax, slug } from './cards'

const FIGHT = { event: 'Byon Combat 40: Main Event', date: '2026-11-01' }
const NAMES = { red: 'Red Fighter', blue: 'Blue Fighter' }

describe('card size', () => {
  it('is Instagram portrait 4:5 at 1080x1350', () => {
    expect([CARD_WIDTH, CARD_HEIGHT]).toEqual([1080, 1350])
    expect(CARD_WIDTH / CARD_HEIGHT).toBe(4 / 5)
  })
})

describe('buildCards', () => {
  const cards = buildCards(sampleStats(), FIGHT, NAMES, 'Tagged with StrikeLens')

  it('makes one card per view, numbered, with matching file names', () => {
    expect(cards.map((c) => c.title)).toEqual([
      'Strike stats',
      'Attempts per round',
      'Weapon mix',
      'Target distribution',
    ])
    expect(cards.map((c) => `${c.index}/${c.total}`)).toEqual(['1/4', '2/4', '3/4', '4/4'])
    expect(cards[0]?.fileName).toBe(
      'strikelens-byon-combat-40-main-event-2026-11-01-1-headline.png',
    )
    expect(cards[3]?.fileName).toBe('strikelens-byon-combat-40-main-event-2026-11-01-4-targets.png')
  })

  it('puts the same header and credit on every card', () => {
    for (const card of cards) {
      expect(card.header).toEqual({ ...FIGHT, names: NAMES })
      expect(card.credit).toBe('Tagged with StrikeLens')
    }
  })

  it('shows headline values from the API, with a dash for undefined', () => {
    const body = cards[0]?.body
    if (body?.kind !== 'headline') throw new Error('expected headline')
    expect(body.rows.find((r) => r.label === 'Accuracy')).toEqual({
      label: 'Accuracy',
      red: '66.7%',
      blue: '—',
    })
    expect(cards[0]?.subtitle).toBe('2 rounds, R2 partial')
  })

  it('keeps null shares as gaps on the target card, on a 0-100% scale', () => {
    const body = cards[3]?.body
    if (body?.kind !== 'bars') throw new Error('expected bars')
    expect(body.max).toBe(1)
    expect(body.categories[0]).toEqual({ label: 'head', red: 0.5, blue: null })
    expect(body.valueLabel(null)).toBe('—')
    expect(body.valueLabel(0.5)).toBe('50.0%')
  })

  it('labels partial rounds on the round card', () => {
    const body = cards[1]?.body
    if (body?.kind !== 'bars') throw new Error('expected bars')
    expect(body.categories.map((c) => c.label)).toEqual(['R1', 'R2 (partial)'])
  })

  it('skips the round card when no round is marked', () => {
    const none = buildCards(sampleStats({ rounds: [] }), FIGHT, NAMES, 'x')
    expect(none.map((c) => c.title)).toEqual(['Strike stats', 'Weapon mix', 'Target distribution'])
    expect(none.at(-1)?.fileName.endsWith('-3-targets.png')).toBe(true)
  })
})

describe('scales', () => {
  it('never uses a zero scale', () => {
    expect(scaleMax([0, null])).toBe(1)
    expect(scaleMax([3, 7, null])).toBe(7)
  })

  it('draws bars as a share of the scale, and null as nothing', () => {
    expect(barHeight(5, 10, 600)).toBe(300)
    expect(barHeight(10, 10, 600)).toBe(600)
    expect(barHeight(20, 10, 600)).toBe(600)
    expect(barHeight(null, 10, 600)).toBe(0)
    expect(barHeight(0, 10, 600)).toBe(0)
  })
})

describe('slug', () => {
  it('makes safe file names', () => {
    expect(slug('Byon Combat 40: Main Event!')).toBe('byon-combat-40-main-event')
    expect(slug('Épée Cup')).toBe('epee-cup')
    expect(slug('***')).toBe('fight')
  })
})
