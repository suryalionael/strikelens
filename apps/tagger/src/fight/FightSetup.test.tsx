import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { api } from '../api/client'
import type { Fight, Fighter, FightInput } from '../api/types'
import { PlayerContext } from '../player/PlayerContext'
import type { Player } from '../player/usePlayerState'
import { fakePlayer } from '../test/fakePlayer'
import { FightSetup } from './FightSetup'
import type { RoundDraft } from './rounds'
import type { SegmentDraft } from './segments'

const RED: Fighter = { id: 'red-1', name: 'Red Fighter', nickname: null, gym: null, country: null }

function fightFrom(input: FightInput, id = 'fight-1'): Fight {
  return { ...input, id }
}

beforeEach(() => {
  vi.spyOn(api, 'listFighters').mockResolvedValue([RED])
  vi.spyOn(api, 'listFights').mockResolvedValue([])
  vi.spyOn(api, 'createFighter').mockImplementation((name) =>
    Promise.resolve({ ...RED, id: 'blue-1', name }),
  )
  vi.spyOn(api, 'createFight').mockImplementation((input) => Promise.resolve(fightFrom(input)))
  vi.spyOn(api, 'replaceFight').mockImplementation((id, input) =>
    Promise.resolve(fightFrom(input, id)),
  )
})

afterEach(() => {
  vi.restoreAllMocks()
})

function Harness({ player, initial = null }: { player: Player; initial?: Fight | null }) {
  const [fight, setFight] = useState<Fight | null>(initial)
  const [rounds, setRounds] = useState<RoundDraft[]>(initial?.rounds ?? [])
  const [segments, setSegments] = useState<SegmentDraft[]>(initial?.segments ?? [])
  return (
    <PlayerContext value={player}>
      <FightSetup
        fight={fight}
        rounds={rounds}
        segments={segments}
        onFightOpen={(opened) => {
          setFight(opened)
          setRounds(opened?.rounds ?? [])
          setSegments(opened?.segments ?? [])
        }}
        onFightSaved={setFight}
        onRoundsChange={setRounds}
        onSegmentsChange={setSegments}
      />
    </PlayerContext>
  )
}

function renderSetup(player = fakePlayer(), initial: Fight | null = null) {
  const view = render(<Harness player={player} initial={initial} />)
  return {
    ...view,
    setTime: (seconds: number) =>
      view.rerender(<Harness player={{ ...player, currentTime: seconds }} initial={initial} />),
  }
}

const savedFight = (rounds: Fight['rounds'] = [], scheduled_rounds = 3): Fight => ({
  id: 'fight-1',
  event: 'Test Event 1',
  date: '2026-11-01',
  red_fighter_id: 'red-1',
  blue_fighter_id: 'blue-1',
  weight_class: null,
  scheduled_rounds,
  video_file: 'fight.mp4',
  rounds,
  segments: [],
  result: null,
})

describe('FightSetup: new fight', () => {
  it('shows what is missing instead of submitting an empty form', async () => {
    renderSetup()
    fireEvent.click(await screen.findByRole('button', { name: 'Create fight' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Event name is required')
    expect(api.createFight).not.toHaveBeenCalled()
  })

  it('creates a new fighter and the fight, then shows the round marker', async () => {
    renderSetup()
    const form = screen.getByRole('form', { name: 'New fight' })
    await screen.findAllByRole('option', { name: 'Red Fighter' })

    fireEvent.change(within(form).getByLabelText('Event'), { target: { value: 'Test Event 1' } })
    fireEvent.change(within(form).getByLabelText('Date'), { target: { value: '2026-11-01' } })
    fireEvent.change(within(form).getByLabelText('Red corner'), { target: { value: 'red-1' } })
    fireEvent.change(within(form).getByLabelText('Blue corner'), { target: { value: '__new__' } })
    fireEvent.change(within(form).getByLabelText('Blue fighter name'), {
      target: { value: ' Blue Fighter ' },
    })
    fireEvent.click(within(form).getByRole('button', { name: 'Create fight' }))

    expect(await screen.findByRole('heading', { name: 'Test Event 1' })).toBeInTheDocument()
    expect(api.createFighter).toHaveBeenCalledWith('Blue Fighter')
    expect(api.createFight).toHaveBeenCalledWith({
      event: 'Test Event 1',
      date: '2026-11-01',
      weight_class: null,
      scheduled_rounds: 3,
      red_fighter_id: 'red-1',
      blue_fighter_id: 'blue-1',
      video_file: 'fight.mp4',
      rounds: [],
      segments: [],
      result: null,
    })
    expect(screen.getByText('Blue Fighter')).toBeInTheDocument()
  })

  it('does not create a fighter twice when the fight save fails and is retried', async () => {
    vi.mocked(api.createFight).mockRejectedValueOnce(new Error('API down'))
    renderSetup()
    await screen.findAllByRole('option', { name: 'Red Fighter' })
    fireEvent.change(screen.getByLabelText('Event'), { target: { value: 'E' } })
    fireEvent.change(screen.getByLabelText('Date'), { target: { value: '2026-11-01' } })
    fireEvent.change(screen.getByLabelText('Red corner'), { target: { value: 'red-1' } })
    fireEvent.change(screen.getByLabelText('Blue corner'), { target: { value: '__new__' } })
    fireEvent.change(screen.getByLabelText('Blue fighter name'), { target: { value: 'Blue' } })

    fireEvent.click(screen.getByRole('button', { name: 'Create fight' }))
    expect(await screen.findByText('API down')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Create fight' }))
    await screen.findByRole('heading', { name: 'E' })
    expect(api.createFighter).toHaveBeenCalledOnce()
  })

  it('opens a saved fight', async () => {
    vi.mocked(api.listFights).mockResolvedValue([savedFight()])
    renderSetup()
    const picker = await screen.findByLabelText('Open a saved fight')
    await screen.findByRole('option', { name: /Test Event 1/ })
    fireEvent.change(picker, { target: { value: 'fight-1' } })
    expect(await screen.findByRole('heading', { name: 'Test Event 1' })).toBeInTheDocument()
  })

  it('shows a clear message when the API is not running', async () => {
    vi.mocked(api.listFighters).mockRejectedValue(new Error('Cannot reach the API'))
    renderSetup()
    expect(await screen.findByText('Cannot reach the API')).toBeInTheDocument()
  })
})

describe('FightSetup: marking rounds', () => {
  it('loads round suggestions and uses them as the rounds', async () => {
    renderSetup(fakePlayer(), savedFight())
    const suggestions = {
      suggestions: [
        { number: 1, start_ms: 179_000, end_ms: 359_000, partial: false, reason: 'Scoreboard' },
        { number: 2, start_ms: 425_000, end_ms: 487_000, partial: true, reason: 'Stoppage?' },
      ],
    }
    const file = new File([JSON.stringify(suggestions)], 'round-suggestions.json')
    fireEvent.change(screen.getByLabelText(/Load round suggestions/), { target: { files: [file] } })

    const list = await screen.findByRole('list', { name: 'Suggested rounds' })
    expect(within(list).getAllByRole('listitem')).toHaveLength(2)
    expect(within(list).getByText('check the end')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Use these rounds' }))

    await waitFor(() =>
      expect(vi.mocked(api.replaceFight).mock.lastCall?.[1].rounds).toEqual([
        { number: 1, start_ms: 179_000, end_ms: 359_000 },
        { number: 2, start_ms: 425_000, end_ms: 487_000 },
      ]),
    )
    expect(screen.queryByRole('list', { name: 'Suggested rounds' })).toBeNull()
    expect(screen.getByLabelText('Round 2 end')).toHaveValue('08:07.000')
  })

  it('offers to replace rounds already marked, and explains a wrong file', async () => {
    renderSetup(fakePlayer(), savedFight([{ number: 1, start_ms: 0, end_ms: 180_000 }]))
    const good = new File(
      [JSON.stringify({ suggestions: [{ number: 1, start_ms: 1000, end_ms: 181_000 }] })],
      'round-suggestions.json',
    )
    fireEvent.change(screen.getByLabelText(/Load round suggestions/), { target: { files: [good] } })
    expect(
      await screen.findByRole('button', { name: 'Replace the marked rounds with these' }),
    ).toBeInTheDocument()

    const bad = new File(['{"shots": []}'], 'cuts.json')
    fireEvent.change(screen.getByLabelText(/Load round suggestions/), { target: { files: [bad] } })
    expect(await screen.findByRole('alert')).toHaveTextContent('No "suggestions" list')
  })

  it('marks start and end at the player time and saves the finished round', async () => {
    const { setTime } = renderSetup(fakePlayer({ currentTime: 1 }), savedFight())

    fireEvent.click(screen.getByRole('button', { name: 'Start round 1 at 00:01.000' }))
    expect(screen.getByText(/Round 1 is open/)).toBeInTheDocument()
    expect(api.replaceFight).not.toHaveBeenCalled()

    setTime(181.25)
    fireEvent.click(screen.getByRole('button', { name: 'End round 1 at 03:01.250' }))
    await waitFor(() => expect(screen.getByText('All rounds saved.')).toBeInTheDocument())
    expect(api.replaceFight).toHaveBeenCalledWith(
      'fight-1',
      expect.objectContaining({ rounds: [{ number: 1, start_ms: 1000, end_ms: 181250 }] }),
    )
    expect(screen.getByRole('button', { name: /Start round 2/ })).toBeInTheDocument()
  })

  it('edits a time by typing and refuses to save overlapping rounds', async () => {
    renderSetup(
      fakePlayer(),
      savedFight([
        { number: 1, start_ms: 0, end_ms: 180000 },
        { number: 2, start_ms: 240000, end_ms: 420000 },
      ]),
    )
    const start2 = screen.getByLabelText('Round 2 start')
    fireEvent.change(start2, { target: { value: '02:50.000' } })
    fireEvent.keyDown(start2, { key: 'Enter' })

    expect(screen.getByRole('alert')).toHaveTextContent('Round 2 starts before round 1 ends')
    expect(api.replaceFight).not.toHaveBeenCalled()

    const fixed = screen.getByLabelText('Round 2 start')
    fireEvent.change(fixed, { target: { value: '03:30' } })
    fireEvent.blur(fixed)
    await waitFor(() => expect(api.replaceFight).toHaveBeenCalledOnce())
    expect(vi.mocked(api.replaceFight).mock.calls[0]?.[1].rounds[1]).toEqual({
      number: 2,
      start_ms: 210000,
      end_ms: 420000,
    })
  })

  it('marks bad typed input without saving it', () => {
    renderSetup(fakePlayer(), savedFight([{ number: 1, start_ms: 0, end_ms: 180000 }]))
    const end1 = screen.getByLabelText('Round 1 end')
    fireEvent.change(end1, { target: { value: 'three minutes' } })
    fireEvent.blur(end1)
    expect(end1).toHaveAttribute('aria-invalid', 'true')
    expect(api.replaceFight).not.toHaveBeenCalled()
  })

  it('supports a fight that ends early and removing the last round', async () => {
    renderSetup(
      fakePlayer(),
      savedFight([
        { number: 1, start_ms: 0, end_ms: 180000 },
        { number: 2, start_ms: 240000, end_ms: 300500 },
      ]),
    )
    expect(screen.getByText('2 of 3 marked')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Remove round 2' }))
    await waitFor(() => expect(api.replaceFight).toHaveBeenCalledOnce())
    expect(vi.mocked(api.replaceFight).mock.calls[0]?.[1].rounds).toHaveLength(1)
  })

  it('stops offering new rounds once all scheduled rounds are marked', () => {
    renderSetup(fakePlayer(), savedFight([{ number: 1, start_ms: 0, end_ms: 1000 }], 1))
    expect(screen.getByText('Every scheduled round is marked.')).toBeInTheDocument()
  })

  it('seeks the player to a round time', () => {
    const player = fakePlayer()
    renderSetup(player, savedFight([{ number: 1, start_ms: 1500, end_ms: 180000 }]))
    fireEvent.click(screen.getByRole('button', { name: 'Go to round 1 start' }))
    expect(player.seek).toHaveBeenCalledWith(1.5)
  })

  it('says when no rounds are marked yet', () => {
    renderSetup(fakePlayer(), savedFight())
    expect(screen.getByText('No rounds marked yet.')).toBeInTheDocument()
  })

  it('keeps a segment when a round is saved while the segment save is in flight', async () => {
    let finishFirst: (fight: Fight) => void = () => undefined
    vi.mocked(api.replaceFight)
      .mockImplementationOnce(
        (_id, input) =>
          new Promise((resolve) => {
            finishFirst = resolve
            void input
          }),
      )
      .mockImplementation((id, input) => Promise.resolve(fightFrom(input, id)))
    const { setTime } = renderSetup(fakePlayer({ currentTime: 1 }), savedFight())

    fireEvent.click(screen.getByRole('button', { name: 'Start replay at 00:01.000' }))
    setTime(5)
    fireEvent.click(screen.getByRole('button', { name: 'End replay at 00:05.000' }))
    fireEvent.click(screen.getByRole('button', { name: 'Start round 1 at 00:05.000' }))
    setTime(185)
    fireEvent.click(screen.getByRole('button', { name: 'End round 1 at 03:05.000' }))

    await waitFor(() => expect(api.replaceFight).toHaveBeenCalledTimes(2))
    expect(vi.mocked(api.replaceFight).mock.lastCall?.[1]).toMatchObject({
      rounds: [{ number: 1, start_ms: 5000, end_ms: 185000 }],
      segments: [{ kind: 'replay', start_ms: 1000, end_ms: 5000 }],
    })
    finishFirst(savedFight())
  })

  it('needs a video before rounds can be marked', () => {
    renderSetup(fakePlayer({ src: null, fileName: null }), savedFight())
    expect(screen.getByRole('button', { name: /Start round 1/ })).toBeDisabled()
  })

  it('warns when a different video is open than the fight was set up with', () => {
    renderSetup(fakePlayer({ fileName: 'other.mp4' }), savedFight())
    expect(screen.getByText(/set up with fight.mp4, but other.mp4 is open/)).toBeInTheDocument()
  })
})
