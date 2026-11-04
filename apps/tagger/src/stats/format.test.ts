import { sampleStats } from '../test/fightStats'
import {
  chartData,
  DASH,
  formatDuration,
  formatPercent,
  formatRate,
  mixRows,
  perRoundRows,
  roundLabel,
  targetRows,
} from './format'

describe('formatting', () => {
  it('shows percentages with one decimal, like the stat definitions', () => {
    expect(formatPercent(199 / 608)).toBe('32.7%')
    expect(formatPercent(0)).toBe('0.0%')
    expect(formatPercent(1)).toBe('100.0%')
  })

  it('shows a dash for undefined values, never zero', () => {
    expect(formatPercent(null)).toBe(DASH)
    expect(formatRate(null)).toBe(DASH)
  })

  it('shows rates with one decimal', () => {
    expect(formatRate(15.888)).toBe('15.9')
    expect(formatRate(0)).toBe('0.0')
  })

  it('shows durations as minutes and seconds', () => {
    expect(formatDuration(0)).toBe('0:00')
    expect(formatDuration(180)).toBe('3:00')
    expect(formatDuration(2310.4)).toBe('38:30')
  })

  it('labels partial rounds', () => {
    expect(roundLabel({ number: 1, partial: false })).toBe('R1')
    expect(roundLabel({ number: 2, partial: true })).toBe('R2 (partial)')
  })
})

describe('reshaping for charts', () => {
  const stats = sampleStats()

  it('puts both corners side by side per round', () => {
    const rows = perRoundRows(stats)
    expect(rows.map((r) => r.label)).toEqual(['R1', 'R2 (partial)'])
    expect(rows[0]?.red.attempts).toBe(2)
    expect(rows[0]?.blue.accuracy).toBeNull()
  })

  it('fills a round missing from a fighter with zero attempts and null rates', () => {
    const missing = sampleStats()
    missing.fighters.blue.by_round = []
    expect(perRoundRows(missing)[0]?.blue).toEqual({
      attempts: 0,
      landed: 0,
      accuracy: null,
      strikes_per_minute: null,
    })
  })

  it('keeps weapon groups in the API order', () => {
    expect(mixRows(stats, 'weapon_groups').map((r) => r.label)).toEqual([
      'punch',
      'kick',
      'knee',
      'elbow',
    ])
  })

  it('picks the landed or attempted target basis', () => {
    expect(targetRows(stats, 'landed')[0]?.red.count).toBe(1)
    expect(targetRows(stats, 'attempted')[0]?.red.count).toBe(2)
  })

  it('flattens rows for a chart and keeps nulls as gaps', () => {
    const data = chartData(targetRows(stats, 'landed'), (v) => v.share)
    expect(data[0]).toEqual({ label: 'head', red: 0.5, blue: null })
  })
})
