import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { api } from '../api/client'
import type { Fight, Tag } from '../api/types'
import type { RoundDraft } from '../fight/rounds'
import { PlayerContext } from '../player/PlayerContext'
import { fakePlayer } from '../test/fakePlayer'
import { TagPanel } from './TagPanel'

const FIGHT = { id: 'fight-1' } as Fight
const ROUNDS: RoundDraft[] = [{ number: 1, start_ms: 1000, end_ms: 181000 }]
const TWO_ROUNDS: RoundDraft[] = [...ROUNDS, { number: 2, start_ms: 190_000, end_ms: 370_000 }]
const video = { currentTime: 0 } as HTMLVideoElement

function suggestion(id: string, ms: number, confidence: number): Tag {
  return {
    id,
    fight_id: 'fight-1',
    round: 1,
    timestamp_ms: ms,
    fighter: 'red',
    weapon: 'kick',
    outcome: null,
    target: null,
    source: 'cv',
    confidence,
    status: 'pending',
    created_by: 'strike-model 0.1',
    created_at: '2026-11-07T10:00:00Z',
  }
}

const HUMAN: Tag = {
  ...suggestion('h1', 3000, 0),
  source: 'human',
  confidence: null,
  status: 'confirmed',
  outcome: 'landed',
  target: 'body',
  weapon: 'jab',
  created_by: 'analyst',
}

let seek: ReturnType<typeof vi.fn<(seconds: number) => void>>

beforeEach(() => {
  video.currentTime = 0
  seek = vi.fn<(seconds: number) => void>()
  vi.spyOn(api, 'listTags').mockResolvedValue([
    HUMAN,
    suggestion('s1', 10_000, 0.9),
    suggestion('s2', 20_000, 0.4),
  ])
  vi.spyOn(api, 'createTag').mockRejectedValue(new Error('should not create'))
  vi.spyOn(api, 'updateTag').mockImplementation((_fight, id, patch) =>
    Promise.resolve({ ...suggestion(id, id === 's1' ? 10_000 : 20_000, 0.9), ...patch } as Tag),
  )
})

afterEach(() => {
  vi.restoreAllMocks()
})

function renderPanel() {
  render(
    <PlayerContext value={fakePlayer({ videoRef: { current: video }, seek })}>
      <TagPanel fight={FIGHT} rounds={ROUNDS} />
    </PlayerContext>,
  )
}

const key = (k: string, mods = {}) => fireEvent.keyDown(window, { key: k, ...mods })

describe('TagPanel: reviewing suggestions', () => {
  it('keeps pending suggestions out of the tag list and count', async () => {
    renderPanel()
    expect(await screen.findByLabelText('Review progress')).toHaveTextContent(
      '0 of 2 reviewed · 2 pending',
    )
    expect(screen.getByText('1 tags')).toBeInTheDocument()
  })

  it('jumps, confirms with outcome and target, then rejects the next', async () => {
    renderPanel()
    fireEvent.click(await screen.findByRole('button', { name: 'Review suggestions' }))

    key('Tab')
    expect(seek).toHaveBeenLastCalledWith(9) // a second before 0:10
    expect(screen.getByLabelText('Current suggestion')).toHaveTextContent(
      'red kick · outcome? · target?',
    )

    key('Enter')
    expect(screen.getByRole('status')).toHaveTextContent('Set the outcome and target first')
    expect(api.updateTag).not.toHaveBeenCalled()

    key('l')
    key('1')
    expect(screen.getByLabelText('Current suggestion')).toHaveTextContent(
      'red kick · landed · head',
    )
    key('Enter')
    await waitFor(() =>
      expect(api.updateTag).toHaveBeenCalledWith('fight-1', 's1', {
        fighter: 'red',
        weapon: 'kick',
        outcome: 'landed',
        target: 'head',
        status: 'confirmed',
      }),
    )
    expect(api.createTag).not.toHaveBeenCalled()
    await waitFor(() => expect(seek).toHaveBeenLastCalledWith(19)) // moved on to 0:20

    key('x')
    await waitFor(() =>
      expect(api.updateTag).toHaveBeenLastCalledWith('fight-1', 's2', { status: 'rejected' }),
    )
    await waitFor(() =>
      expect(screen.getByLabelText('Review progress')).toHaveTextContent(
        '2 of 2 reviewed · 0 pending',
      ),
    )
    expect(screen.getByText('2 tags')).toBeInTheDocument() // the confirmed suggestion counts
  })

  it('lets the analyst change the weapon before confirming', async () => {
    renderPanel()
    fireEvent.click(await screen.findByRole('button', { name: 'Review suggestions' }))
    key('Tab')
    key('t')
    key('m')
    key('2')
    key('Enter')
    await waitFor(() =>
      expect(api.updateTag).toHaveBeenCalledWith(
        'fight-1',
        's1',
        expect.objectContaining({ weapon: 'teep', outcome: 'missed', target: 'body' }),
      ),
    )
  })

  it('filters by confidence', async () => {
    renderPanel()
    const slider = await screen.findByRole('slider')
    fireEvent.change(slider, { target: { value: '0.5' } })
    expect(screen.getByLabelText('Review progress')).toHaveTextContent(
      '0 of 1 reviewed · 1 pending',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Review suggestions' }))
    key('Tab')
    key('Tab')
    expect(seek).toHaveBeenLastCalledWith(9) // only 0:10 passes the filter
  })

  it('undoes a confirmation back to pending', async () => {
    renderPanel()
    fireEvent.click(await screen.findByRole('button', { name: 'Review suggestions' }))
    key('Tab')
    key('l')
    key('1')
    key('Enter')
    await waitFor(() => expect(api.updateTag).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Confirmed'))
    key('z', { ctrlKey: true })
    await waitFor(() =>
      expect(api.updateTag).toHaveBeenLastCalledWith(
        'fight-1',
        's1',
        expect.objectContaining({ status: 'pending' }),
      ),
    )
  })

  it('tags as usual when not reviewing', async () => {
    renderPanel()
    await screen.findByRole('button', { name: 'Review suggestions' })
    key('Tab')
    key('Enter')
    expect(seek).not.toHaveBeenCalled()
    expect(api.updateTag).not.toHaveBeenCalled()
  })

  it('reviews one round at a time, starting with the round at the playhead', async () => {
    vi.mocked(api.listTags).mockResolvedValue([
      suggestion('a1', 10_000, 0.9),
      { ...suggestion('b1', 200_000, 0.9), round: 2, weapon: null },
      { ...suggestion('b2', 210_000, 0.9), round: 2 },
    ])
    video.currentTime = 195 // inside round 2
    render(
      <PlayerContext value={fakePlayer({ videoRef: { current: video }, seek })}>
        <TagPanel fight={FIGHT} rounds={TWO_ROUNDS} />
      </PlayerContext>,
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Review suggestions' }))
    expect(screen.getByLabelText('Review progress')).toHaveTextContent(
      'Round 2: 0 of 2 reviewed · 2 pending',
    )
    key('Tab')
    expect(screen.getByLabelText('Current suggestion')).toHaveTextContent(
      'red weapon? · outcome? · target?',
    )
    key('Tab')
    key('Tab') // wraps inside round 2, never to round 1
    expect(seek).not.toHaveBeenCalledWith(9)

    fireEvent.change(screen.getByRole('combobox', { name: 'Round' }), { target: { value: 'all' } })
    expect(screen.getByLabelText('Review progress')).toHaveTextContent(
      'Whole fight: 0 of 3 reviewed · 3 pending',
    )
  })
})
