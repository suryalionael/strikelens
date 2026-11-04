import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { api } from '../api/client'
import type { Fight } from '../api/types'
import { sampleStats } from '../test/fightStats'
import { makeTag } from '../test/tag'
import type { Card } from './cards'
import { canvasToPng, downloadBlob, downloadText, renderCard } from './download'
import { ExportPanel } from './ExportPanel'

// jsdom has no canvas; the drawing itself is tested in draw.test.ts.
vi.mock('./download', () => ({
  renderCard: vi.fn((card: Card) => ({ toDataURL: () => `data:image/png;base64,${card.index}` })),
  canvasToPng: vi.fn(() => Promise.resolve(new Blob(['png']))),
  downloadBlob: vi.fn(),
  downloadText: vi.fn(),
}))

const FIGHT = { id: 'fight-1', event: 'Test Event 1', date: '2026-11-01' } as Fight
const NAMES = { red: 'Red Fighter', blue: 'Blue Fighter' }

function renderPanel() {
  render(<ExportPanel fight={FIGHT} stats={sampleStats()} names={NAMES} />)
}

afterEach(() => {
  vi.clearAllMocks()
  vi.restoreAllMocks()
})

describe('ExportPanel', () => {
  it('downloads one PNG per card', async () => {
    renderPanel()
    fireEvent.click(screen.getByRole('button', { name: 'Download cards (PNG)' }))
    await waitFor(() => expect(downloadBlob).toHaveBeenCalledTimes(4))
    expect(vi.mocked(downloadBlob).mock.calls.map((c) => c[1])).toEqual([
      'strikelens-test-event-1-2026-11-01-1-headline.png',
      'strikelens-test-event-1-2026-11-01-2-rounds.png',
      'strikelens-test-event-1-2026-11-01-3-weapons.png',
      'strikelens-test-event-1-2026-11-01-4-targets.png',
    ])
    expect(canvasToPng).toHaveBeenCalledTimes(4)
    expect(screen.getByRole('status')).toHaveTextContent('Downloaded 4 cards (1080×1350 PNG).')
  })

  it('puts the edited credit line on every card', async () => {
    renderPanel()
    fireEvent.change(screen.getByLabelText(/Credit line/), { target: { value: 'Stats: Freefly' } })
    fireEvent.click(screen.getByRole('button', { name: 'Download cards (PNG)' }))
    await waitFor(() => expect(renderCard).toHaveBeenCalledTimes(4))
    for (const [card] of vi.mocked(renderCard).mock.calls)
      expect(card.credit).toBe('Stats: Freefly')
  })

  it('falls back to the default credit when the field is cleared', async () => {
    renderPanel()
    fireEvent.change(screen.getByLabelText(/Credit line/), { target: { value: '  ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview cards' }))
    expect(vi.mocked(renderCard).mock.calls[0]?.[0].credit).toBe('Tagged with StrikeLens')
  })

  it('previews every card', () => {
    renderPanel()
    fireEvent.click(screen.getByRole('button', { name: 'Preview cards' }))
    expect(screen.getAllByRole('img')).toHaveLength(4)
  })

  it('downloads the confirmed tags as CSV, fetched fresh', async () => {
    vi.spyOn(api, 'listTags').mockResolvedValue([
      makeTag({ id: 'a' }),
      makeTag({ id: 'p', status: 'pending', source: 'cv', confidence: 0.7 }),
    ])
    renderPanel()
    fireEvent.click(screen.getByRole('button', { name: 'Tags (CSV)' }))
    await waitFor(() => expect(downloadText).toHaveBeenCalledOnce())
    const [csv, name, type] = vi.mocked(downloadText).mock.calls[0] ?? []
    expect(name).toBe('strikelens-test-event-1-2026-11-01-tags.csv')
    expect(type).toBe('text/csv')
    expect(csv?.trimEnd().split('\r\n')).toHaveLength(2)
    expect(screen.getByRole('status')).toHaveTextContent('Downloaded 1 confirmed tags.')
  })

  it('downloads the stats summary as CSV', () => {
    renderPanel()
    fireEvent.click(screen.getByRole('button', { name: 'Stats (CSV)' }))
    const [csv, name] = vi.mocked(downloadText).mock.calls[0] ?? []
    expect(name).toBe('strikelens-test-event-1-2026-11-01-stats.csv')
    expect(csv?.startsWith('group,item,fighter,metric,value')).toBe(true)
  })

  it('says why a download failed', async () => {
    vi.spyOn(api, 'listTags').mockRejectedValue(new Error('API down'))
    renderPanel()
    fireEvent.click(screen.getByRole('button', { name: 'Tags (CSV)' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('API down')
  })
})
