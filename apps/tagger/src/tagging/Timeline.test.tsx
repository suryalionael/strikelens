import { fireEvent, render, screen, within } from '@testing-library/react'
import type { Tag } from '../api/types'
import type { RoundDraft } from '../fight/rounds'
import { PlayerContext } from '../player/PlayerContext'
import type { Player } from '../player/usePlayerState'
import { fakePlayer } from '../test/fakePlayer'
import { Timeline } from './Timeline'
import { markers } from './timelineLayout'

// Count how often markers are built, to prove the playhead does not rebuild them.
vi.mock('./timelineLayout', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./timelineLayout')>()
  return { ...actual, markers: vi.fn(actual.markers) }
})

const ROUNDS: RoundDraft[] = [
  { number: 1, start_ms: 0, end_ms: 100_000 },
  { number: 2, start_ms: 150_000, end_ms: 250_000 },
]

function tag(id: string, overrides: Partial<Tag> = {}): Tag {
  return {
    id,
    fight_id: 'f1',
    round: 1,
    timestamp_ms: 50_000,
    fighter: 'red',
    weapon: 'kick',
    outcome: 'landed',
    target: 'body',
    source: 'human',
    confidence: null,
    status: 'confirmed',
    created_by: 'analyst',
    created_at: '2026-11-04T10:00:00Z',
    ...overrides,
  }
}

const TAGS: Tag[] = [
  tag('a'),
  tag('b', { fighter: 'blue', outcome: 'missed', timestamp_ms: 60_000, weapon: 'jab' }),
  tag('c', { round: 2, outcome: 'blocked', timestamp_ms: 200_000, weapon: 'teep' }),
  tag('d', { status: 'pending', timestamp_ms: 70_000 }),
]

function renderTimeline(player: Player = fakePlayer(), tags = TAGS, rounds = ROUNDS) {
  const view = render(
    <PlayerContext value={player}>
      <Timeline tags={tags} rounds={rounds} />
    </PlayerContext>,
  )
  return {
    ...view,
    rerenderAt: (seconds: number) =>
      view.rerender(
        <PlayerContext value={{ ...player, currentTime: seconds }}>
          <Timeline tags={tags} rounds={rounds} />
        </PlayerContext>,
      ),
  }
}

const left = (el: HTMLElement) => Number.parseFloat(el.style.left)

beforeEach(() => {
  vi.mocked(markers).mockClear()
})

describe('Timeline', () => {
  it('puts confirmed tags on their fighter lane', () => {
    renderTimeline()
    const red = screen.getByLabelText('Red lane')
    const blue = screen.getByLabelText('Blue lane')
    expect(within(red).getAllByRole('button')).toHaveLength(2)
    expect(within(blue).getAllByRole('button')).toHaveLength(1)
    expect(
      within(blue).getByRole('button', { name: 'Blue jab missed body at 01:00.000, round 1' }),
    ).toBeInTheDocument()
  })

  it('shows outcome by shape: filled, ring, square', () => {
    renderTimeline()
    const landed = screen.getByRole('button', { name: /Red kick landed/ })
    const missed = screen.getByRole('button', { name: /Blue jab missed/ })
    const blocked = screen.getByRole('button', { name: /Red teep blocked/ })
    expect(landed).toHaveClass('rounded-full')
    expect(landed.style.background).not.toBe('transparent')
    expect(missed.style.background).toBe('transparent')
    expect(missed.style.border).toContain('2px solid')
    expect(blocked).toHaveClass('rounded-[1px]')
  })

  it('spans the rounds and shows each round band', () => {
    renderTimeline()
    const r1 = screen.getByTestId('round-band-1')
    const r2 = screen.getByTestId('round-band-2')
    expect(left(r1)).toBeLessThan(left(r2))
    expect(screen.getByText('R1')).toBeInTheDocument()
    expect(screen.getByText('R2')).toBeInTheDocument()
    // Round 1 runs 0-100 s and round 2 150-250 s; the 50 s break is left empty.
    expect(left(r2)).toBeGreaterThan(left(r1) + Number.parseFloat(r1.style.width))
  })

  it('draws replays and non-fight segments as labelled bands', () => {
    render(
      <PlayerContext value={fakePlayer()}>
        <Timeline
          tags={TAGS}
          rounds={ROUNDS}
          segments={[
            { kind: 'replay', start_ms: 40_000, end_ms: 45_000 },
            { kind: 'non_fight', start_ms: 100_000, end_ms: 150_000 },
          ]}
        />
      </PlayerContext>,
    )
    expect(screen.getByRole('img', { name: 'Replay 00:40.000 to 00:45.000' })).toBeInTheDocument()
    expect(screen.getByTestId('segment-band-non_fight')).toBeInTheDocument()
    expect(screen.getByText('non-fight')).toBeInTheDocument()
  })

  it('labels an open round', () => {
    renderTimeline(fakePlayer({ currentTime: 300 }), TAGS, [
      ...ROUNDS,
      { number: 3, start_ms: 280_000, end_ms: null },
    ])
    expect(screen.getByText('R3 (open)')).toBeInTheDocument()
  })

  it('jumps the video to a marker when it is clicked', () => {
    const player = fakePlayer()
    renderTimeline(player)
    fireEvent.click(screen.getByRole('button', { name: /Red teep blocked/ }))
    expect(player.seek).toHaveBeenCalledWith(200)
    expect(player.seek).toHaveBeenCalledOnce()
  })

  it('jumps the video to the clicked point on the track', () => {
    const player = fakePlayer()
    renderTimeline(player)
    const track = screen.getByTestId('timeline-track')
    vi.spyOn(track, 'getBoundingClientRect').mockReturnValue({
      left: 100,
      width: 400,
    } as DOMRect)
    fireEvent.click(track, { clientX: 300 })
    // Rounds span 0-250 s; 2% padding adds 5 s at the end (the start is clamped at
    // 0), so the range is 0-255 s and halfway is 127.5 s.
    expect(player.seek).toHaveBeenCalledWith(127.5)
  })

  it('moves the playhead with the video', () => {
    const { rerenderAt } = renderTimeline(fakePlayer({ currentTime: 0 }))
    const start = left(screen.getByTestId('playhead'))
    rerenderAt(127.5)
    expect(left(screen.getByTestId('playhead'))).toBeGreaterThan(start)
    expect(left(screen.getByTestId('playhead'))).toBeCloseTo(50)
  })

  it('does not rebuild markers when only the playhead moves', () => {
    const { rerenderAt } = renderTimeline()
    const builds = vi.mocked(markers).mock.calls.length
    for (let s = 1; s <= 30; s++) rerenderAt(s)
    expect(vi.mocked(markers).mock.calls.length).toBe(builds)
  })

  it('renders 300+ tags', () => {
    const many = Array.from({ length: 400 }, (_, i) =>
      tag(`t${i}`, {
        fighter: i % 2 ? 'blue' : 'red',
        timestamp_ms: (i * 600) % 250_000,
        round: (i * 600) % 250_000 < 125_000 ? 1 : 2,
      }),
    )
    const started = performance.now()
    renderTimeline(fakePlayer(), many)
    const elapsed = performance.now() - started
    expect(within(screen.getByLabelText('Red lane')).getAllByRole('button')).toHaveLength(200)
    expect(within(screen.getByLabelText('Blue lane')).getAllByRole('button')).toHaveLength(200)
    // A generous budget: this guards against accidental quadratic work, not speed.
    expect(elapsed).toBeLessThan(2_000)
  })
})
