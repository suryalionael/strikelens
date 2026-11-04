import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { api } from '../api/client'
import type { Fight, Tag, TagInput } from '../api/types'
import type { RoundDraft } from '../fight/rounds'
import { PlayerContext } from '../player/PlayerContext'
import { fakePlayer } from '../test/fakePlayer'
import { TagPanel } from './TagPanel'

const FIGHT = { id: 'fight-1' } as Fight
const ROUNDS: RoundDraft[] = [{ number: 1, start_ms: 1000, end_ms: 181000 }]

let videoTime = 61.25
const video = {
  get currentTime() {
    return videoTime
  },
} as HTMLVideoElement

function saved(input: TagInput, n: number): Tag {
  return { ...input, id: `tag-${n}`, fight_id: 'fight-1', created_at: '2026-11-04T10:00:00Z' }
}

beforeEach(() => {
  videoTime = 61.25
  let n = 0
  vi.spyOn(api, 'listTags').mockResolvedValue([])
  vi.spyOn(api, 'createTag').mockImplementation((_id, input) => Promise.resolve(saved(input, ++n)))
})

afterEach(() => {
  vi.restoreAllMocks()
})

function renderPanel({
  fight = FIGHT as Fight | null,
  rounds = ROUNDS,
  src = 'blob:fight' as string | null,
} = {}) {
  return render(
    <PlayerContext value={fakePlayer({ src, videoRef: { current: video } })}>
      <TagPanel fight={fight} rounds={rounds} />
    </PlayerContext>,
  )
}

const keys = (...pressed: string[]) => {
  for (const key of pressed) fireEvent.keyDown(window, { key })
}

describe('TagPanel', () => {
  it('asks for a fight, then for a video', () => {
    const { unmount } = renderPanel({ fight: null })
    expect(screen.getByText('Open or create a fight to start tagging.')).toBeInTheDocument()
    unmount()
    renderPanel({ src: null })
    expect(screen.getByText('Open the fight video to start tagging.')).toBeInTheDocument()
    keys('q', 'k', 'l', '2')
    expect(api.createTag).not.toHaveBeenCalled()
  })

  it('saves Q K L 2 as a confirmed human tag at the first key time', async () => {
    renderPanel()
    keys('q')
    videoTime = 62
    keys('k', 'l', '2')
    await screen.findByText(/^Saved red kick landed body at 01:01.250, round 1/)
    expect(api.createTag).toHaveBeenCalledWith('fight-1', {
      round: 1,
      timestamp_ms: 61250,
      fighter: 'red',
      weapon: 'kick',
      outcome: 'landed',
      target: 'body',
      source: 'human',
      confidence: null,
      status: 'confirmed',
      created_by: 'analyst',
    })
    expect(screen.getByRole('table')).toHaveTextContent('kick · landed · body')
    expect(screen.getByText('1 tags')).toBeInTheDocument()
  })

  it('keeps the fighter for the next tag', async () => {
    renderPanel()
    keys('w', 'j', 'm', '1')
    await waitFor(() => expect(api.createTag).toHaveBeenCalledTimes(1))
    videoTime = 70
    keys('t', 'b', '2')
    await waitFor(() => expect(api.createTag).toHaveBeenCalledTimes(2))
    expect(vi.mocked(api.createTag).mock.calls[1]?.[1]).toMatchObject({
      fighter: 'blue',
      weapon: 'teep',
      timestamp_ms: 70000,
    })
  })

  it('shows the draft as keys are pressed and clears it with Esc', () => {
    renderPanel()
    keys('q', 'h')
    expect(screen.getByText('Tag at 01:01.250 · Esc to clear')).toBeInTheDocument()
    expect(screen.getByText('hook').closest('[aria-current]')).toHaveAttribute(
      'aria-current',
      'true',
    )
    keys('Escape')
    expect(screen.getByText('Press a key to start a tag')).toBeInTheDocument()
    keys('l', '1')
    expect(api.createTag).not.toHaveBeenCalled()
  })

  it('refuses a tag outside every round and says why', async () => {
    videoTime = 200
    renderPanel()
    keys('q', 'k', 'l', '2')
    expect(
      await screen.findByText('Not saved: 03:20.000 is outside every marked round.'),
    ).toBeInTheDocument()
    expect(api.createTag).not.toHaveBeenCalled()
  })

  it('tags into a round that has started but not ended', async () => {
    videoTime = 500
    renderPanel({ rounds: [...ROUNDS, { number: 2, start_ms: 241000, end_ms: null }] })
    keys('q', 'k', 'l', '2')
    await waitFor(() => expect(api.createTag).toHaveBeenCalledOnce())
    expect(vi.mocked(api.createTag).mock.calls[0]?.[1].round).toBe(2)
  })

  it('ignores keys typed into a text field', () => {
    renderPanel()
    const input = document.createElement('input')
    document.body.append(input)
    for (const key of ['q', 'k', 'l', '2']) fireEvent.keyDown(input, { key })
    expect(api.createTag).not.toHaveBeenCalled()
    input.remove()
  })

  it('reports an API failure with the tag it lost', async () => {
    vi.mocked(api.createTag).mockRejectedValueOnce(new Error('API down'))
    renderPanel()
    keys('q', 'k', 'l', '2')
    expect(
      await screen.findByText('Not saved (red kick landed body at 01:01.250, round 1): API down'),
    ).toBeInTheDocument()
  })

  it('loads the fight’s existing tags, newest first', async () => {
    const base: TagInput = {
      round: 1,
      timestamp_ms: 0,
      fighter: 'red',
      weapon: 'jab',
      outcome: 'landed',
      target: 'head',
      source: 'human',
      confidence: null,
      status: 'confirmed',
      created_by: 'analyst',
    }
    vi.mocked(api.listTags).mockResolvedValue([
      saved({ ...base, timestamp_ms: 5000 }, 1),
      saved({ ...base, timestamp_ms: 9000, weapon: 'kick' }, 2),
    ])
    renderPanel()
    expect(await screen.findByText('2 tags')).toBeInTheDocument()
    const rows = screen.getAllByRole('row').slice(1)
    expect(rows[0]).toHaveTextContent('00:09.000')
    expect(rows[1]).toHaveTextContent('00:05.000')
  })
})
