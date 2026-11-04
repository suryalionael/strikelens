import { sampleStats } from '../test/fightStats'
import { buildCards, CARD_HEIGHT, CARD_WIDTH, PROVISIONAL_NOTE } from './cards'
import { drawCard, fitText, type Ctx } from './draw'

/** A canvas context that records what is drawn. Text is 10px per character. */
function recorder() {
  const texts: string[] = []
  const rects: number[][] = []
  const bars: number[][] = []
  const ctx: Ctx = {
    fillStyle: '',
    font: '',
    textAlign: 'left',
    textBaseline: 'alphabetic',
    fillRect: (x, y, w, h) => {
      rects.push([x, y, w, h])
    },
    fillText: (value) => {
      texts.push(value)
    },
    measureText: (value) => ({ width: value.length * 10 }) as TextMetrics,
    beginPath: () => undefined,
    roundRect: (x, y, w, h) => {
      bars.push([x, y, w, h])
    },
    fill: () => undefined,
  }
  return { ctx, texts, rects, bars }
}

const NAMES = { red: 'Red Fighter', blue: 'Blue Fighter' }
const cards = buildCards(
  sampleStats(),
  { event: 'Test Event 1', date: '2026-11-01' },
  NAMES,
  'Tagged with StrikeLens',
)

describe('drawCard', () => {
  it('fills the whole 1080x1350 card first', () => {
    const r = recorder()
    const card = cards[0]
    if (!card) throw new Error('no card')
    drawCard(r.ctx, card)
    expect(r.rects[0]).toEqual([0, 0, CARD_WIDTH, CARD_HEIGHT])
  })

  it('puts the header, credit, provisional note, and page number on every card', () => {
    for (const card of cards) {
      const r = recorder()
      drawCard(r.ctx, card)
      expect(r.texts).toContain(card.title)
      expect(r.texts).toContain('Test Event 1 · 2026-11-01')
      expect(r.texts).toContain('Red: Red Fighter')
      expect(r.texts).toContain('Blue: Blue Fighter')
      expect(r.texts).toContain(PROVISIONAL_NOTE)
      expect(r.texts).toContain('Tagged with StrikeLens')
      expect(r.texts).toContain(`${card.index}/${card.total}`)
    }
  })

  it('draws a dash and no bar for an undefined value', () => {
    const r = recorder()
    const targets = cards[3]
    if (!targets) throw new Error('no card')
    drawCard(r.ctx, targets)
    // Blue has no landed strikes: three dashes, and only red's three bars minus legs (0%).
    expect(r.texts.filter((t) => t === '—')).toHaveLength(3)
    expect(r.bars.filter((b) => (b[3] ?? 0) > 24)).toHaveLength(2)
  })

  it('shows the headline numbers', () => {
    const r = recorder()
    const headline = cards[0]
    if (!headline) throw new Error('no card')
    drawCard(r.ctx, headline)
    expect(r.texts).toEqual(expect.arrayContaining(['Accuracy', '66.7%', '—', '0.5', '0.0']))
  })
})

describe('fitText', () => {
  it('leaves short text alone and shortens long text with an ellipsis', () => {
    const { ctx } = recorder()
    expect(fitText(ctx, 'short', 100)).toBe('short')
    expect(fitText(ctx, 'a very long fighter name', 100)).toBe('a very lo…')
  })
})
