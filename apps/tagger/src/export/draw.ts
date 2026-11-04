import type { Corner } from '../api/types'
import { CORNER_COLOR, CORNER_NAME } from '../stats/colors'
import {
  barHeight,
  CARD_HEIGHT,
  CARD_WIDTH,
  PROVISIONAL_NOTE,
  type BarsBody,
  type Card,
} from './cards'

/** The parts of the canvas API the cards use, so tests can record the calls. */
export type Ctx = Pick<
  CanvasRenderingContext2D,
  | 'fillStyle'
  | 'font'
  | 'textAlign'
  | 'textBaseline'
  | 'fillRect'
  | 'fillText'
  | 'measureText'
  | 'beginPath'
  | 'roundRect'
  | 'fill'
>

const PAD = 80
const BG = '#0a0a0a'
const INK = '#f5f5f5'
const MUTED = '#a3a3a3'
const FAINT = '#525252'
const GRID = '#262626'
const NOTE = '#fbbf24'
const FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
const CORNERS: Corner[] = ['red', 'blue']

const font = (size: number, weight = 400) => `${weight} ${size}px ${FONT}`

/** Shorten text with an ellipsis until it fits `max` pixels. */
export function fitText(ctx: Ctx, text: string, max: number): string {
  if (ctx.measureText(text).width <= max) return text
  let cut = text
  while (cut.length > 1 && ctx.measureText(`${cut}…`).width > max) cut = cut.slice(0, -1)
  return `${cut}…`
}

function text(
  ctx: Ctx,
  value: string,
  x: number,
  y: number,
  opts: { size: number; weight?: number; color?: string; align?: CanvasTextAlign; max?: number },
) {
  ctx.font = font(opts.size, opts.weight)
  ctx.fillStyle = opts.color ?? INK
  ctx.textAlign = opts.align ?? 'left'
  ctx.textBaseline = 'alphabetic'
  ctx.fillText(opts.max ? fitText(ctx, value, opts.max) : value, x, y)
}

function swatch(ctx: Ctx, corner: Corner, x: number, y: number, size = 24) {
  ctx.fillStyle = CORNER_COLOR[corner]
  ctx.beginPath()
  ctx.roundRect(x, y, size, size, 4)
  ctx.fill()
}

function drawHeader(ctx: Ctx, card: Card) {
  text(ctx, `${card.header.event} · ${card.header.date}`, PAD, PAD + 30, {
    size: 30,
    color: MUTED,
    max: CARD_WIDTH - 2 * PAD,
  })
  text(ctx, card.title, PAD, PAD + 110, { size: 68, weight: 700 })
  if (card.subtitle) text(ctx, card.subtitle, PAD, PAD + 160, { size: 30, color: MUTED })
  const half = (CARD_WIDTH - 2 * PAD) / 2
  CORNERS.forEach((corner, i) => {
    const x = PAD + i * half
    swatch(ctx, corner, x, PAD + 200)
    text(ctx, `${CORNER_NAME[corner]}: ${card.header.names[corner]}`, x + 38, PAD + 222, {
      size: 32,
      weight: 600,
      max: half - 50,
    })
  })
}

function drawFooter(ctx: Ctx, card: Card) {
  const y = CARD_HEIGHT - PAD
  text(ctx, PROVISIONAL_NOTE, PAD, y - 50, { size: 26, color: NOTE })
  text(ctx, card.credit, PAD, y, { size: 28, color: MUTED, max: CARD_WIDTH - 2 * PAD - 120 })
  text(ctx, `${card.index}/${card.total}`, CARD_WIDTH - PAD, y, {
    size: 28,
    color: FAINT,
    align: 'right',
  })
}

const BODY_TOP = PAD + 300
const BODY_BOTTOM = CARD_HEIGHT - PAD - 120

function drawHeadline(ctx: Ctx, rows: { label: string; red: string; blue: string }[]) {
  const rowHeight = (BODY_BOTTOM - BODY_TOP) / rows.length
  // Red's column sits right of centre so a long label never meets a wide value.
  const valueX = [CARD_WIDTH * 0.66, CARD_WIDTH - PAD]
  rows.forEach((row, i) => {
    const top = BODY_TOP + i * rowHeight
    ctx.fillStyle = GRID
    ctx.fillRect(PAD, top, CARD_WIDTH - 2 * PAD, 2)
    const baseline = top + rowHeight / 2 + 26
    text(ctx, row.label, PAD, baseline, { size: 36, color: MUTED })
    CORNERS.forEach((corner, c) => {
      text(ctx, row[corner], valueX[c] ?? 0, baseline, { size: 76, weight: 700, align: 'right' })
    })
  })
}

function drawBars(ctx: Ctx, body: BarsBody) {
  const chartTop = BODY_TOP + 70
  const chartBottom = BODY_BOTTOM - 70
  const height = chartBottom - chartTop
  const width = CARD_WIDTH - 2 * PAD
  const slot = width / body.categories.length
  const bar = Math.min(80, slot / 3.5)
  // Wide enough that two value labels like "33.3%" never touch.
  const gap = 28

  ctx.fillStyle = GRID
  ctx.fillRect(PAD, chartBottom, width, 2)

  body.categories.forEach((cat, i) => {
    const centre = PAD + slot * i + slot / 2
    CORNERS.forEach((corner, c) => {
      const value = cat[corner]
      const x = c === 0 ? centre - gap / 2 - bar : centre + gap / 2
      const h = barHeight(value, body.max, height - 60)
      if (h > 0) {
        ctx.fillStyle = CORNER_COLOR[corner]
        ctx.beginPath()
        ctx.roundRect(x, chartBottom - h, bar, h, [10, 10, 0, 0])
        ctx.fill()
      }
      text(ctx, body.valueLabel(value), x + bar / 2, chartBottom - h - 16, {
        size: 28,
        weight: 600,
        align: 'center',
      })
    })
    text(ctx, cat.label, centre, chartBottom + 56, {
      size: 32,
      color: MUTED,
      align: 'center',
      max: slot - 12,
    })
  })
}

/** Draw one 1080x1350 card. The same header and footer go on every card. */
export function drawCard(ctx: Ctx, card: Card) {
  ctx.fillStyle = BG
  ctx.fillRect(0, 0, CARD_WIDTH, CARD_HEIGHT)
  drawHeader(ctx, card)
  if (card.body.kind === 'headline') drawHeadline(ctx, card.body.rows)
  else drawBars(ctx, card.body)
  drawFooter(ctx, card)
}
