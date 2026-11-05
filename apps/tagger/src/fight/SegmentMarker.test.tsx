import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { api } from '../api/client'
import type { Fight } from '../api/types'
import { PlayerContext } from '../player/PlayerContext'
import type { Player } from '../player/usePlayerState'
import { fakePlayer } from '../test/fakePlayer'
import { SegmentMarker } from './SegmentMarker'
import type { SegmentDraft } from './segments'

const FIGHT: Fight = {
  id: 'fight-1',
  event: 'Test Event 1',
  date: '2026-11-01',
  red_fighter_id: 'red-1',
  blue_fighter_id: 'blue-1',
  weight_class: null,
  scheduled_rounds: 3,
  video_file: 'fight.mp4',
  rounds: [{ number: 1, start_ms: 0, end_ms: 180_000 }],
  segments: [],
  result: null,
}

beforeEach(() => {
  vi.spyOn(api, 'replaceFight').mockImplementation((id, input) => Promise.resolve({ ...input, id }))
})

afterEach(() => {
  vi.restoreAllMocks()
})

function Harness({ player }: { player: Player }) {
  const [fight, setFight] = useState(FIGHT)
  const [segments, setSegments] = useState<SegmentDraft[]>([])
  return (
    <PlayerContext value={player}>
      <SegmentMarker
        fight={fight}
        segments={segments}
        rounds={fight.rounds}
        onSegmentsChange={setSegments}
        onSaved={setFight}
      />
    </PlayerContext>
  )
}

function renderMarker(player = fakePlayer()) {
  const view = render(<Harness player={player} />)
  return {
    ...view,
    setTime: (seconds: number) =>
      view.rerender(<Harness player={{ ...player, currentTime: seconds }} />),
  }
}

describe('SegmentMarker', () => {
  it('marks a replay and saves it with the fight’s rounds', async () => {
    const { setTime } = renderMarker()
    setTime(60)
    fireEvent.click(screen.getByRole('button', { name: 'Start replay at 01:00.000' }))
    expect(screen.getByText('Replay is open. It is saved when you mark its end.')).toBeVisible()
    expect(api.replaceFight).not.toHaveBeenCalled()

    setTime(72.5)
    fireEvent.click(screen.getByRole('button', { name: 'End replay at 01:12.500' }))
    await waitFor(() => expect(screen.getByText('All segments saved.')).toBeVisible())
    expect(api.replaceFight).toHaveBeenCalledWith('fight-1', {
      ...FIGHT,
      id: undefined,
      segments: [{ kind: 'replay', start_ms: 60_000, end_ms: 72_500 }],
    })
  })

  it('does not save a segment that ends before it starts', () => {
    const { setTime } = renderMarker()
    setTime(60)
    fireEvent.click(screen.getByRole('button', { name: 'Start non-fight at 01:00.000' }))
    setTime(10)
    fireEvent.click(screen.getByRole('button', { name: 'End non-fight at 00:10.000' }))
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Non-fight at 01:00.000 ends before it starts',
    )
    expect(api.replaceFight).not.toHaveBeenCalled()
  })

  it('removes a segment', async () => {
    const { setTime } = renderMarker()
    fireEvent.click(screen.getByRole('button', { name: 'Start replay at 00:00.000' }))
    setTime(5)
    fireEvent.click(screen.getByRole('button', { name: 'End replay at 00:05.000' }))
    fireEvent.click(screen.getByRole('button', { name: 'Remove replay at 00:00.000' }))
    await waitFor(() => expect(screen.getByText('No segments marked.')).toBeVisible())
    expect(vi.mocked(api.replaceFight).mock.lastCall?.[1].segments).toEqual([])
  })

  it('needs a video to mark', () => {
    renderMarker(fakePlayer({ src: null }))
    expect(screen.getByRole('button', { name: /Start replay/ })).toBeDisabled()
  })

  it('loads suggestions and accepts or dismisses them', async () => {
    renderMarker()
    const suggestions = {
      suggestions: [
        { kind: 'replay', start_ms: 60_000, end_ms: 63_000, reason: '3 shots in a row' },
        { kind: 'replay', start_ms: 90_000, end_ms: 95_000, reason: '4 shots in a row' },
      ],
    }
    const file = new File([JSON.stringify(suggestions)], 'segment-suggestions.json')
    fireEvent.change(screen.getByLabelText(/Load suggestions/), { target: { files: [file] } })

    const list = await screen.findByRole('list', { name: 'Suggested segments' })
    expect(within(list).getAllByRole('listitem')).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'Accept replay 01:00.000 to 01:03.000' }))
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss replay 01:30.000 to 01:35.000' }))

    expect(await screen.findByText('No suggestions left.')).toBeVisible()
    await waitFor(() =>
      expect(vi.mocked(api.replaceFight).mock.lastCall?.[1].segments).toEqual([
        { kind: 'replay', start_ms: 60_000, end_ms: 63_000 },
      ]),
    )
  })

  it('explains a file that is not a suggestions file', async () => {
    renderMarker()
    const file = new File(['{"shots": []}'], 'cuts.json')
    fireEvent.change(screen.getByLabelText(/Load suggestions/), { target: { files: [file] } })
    expect(await screen.findByRole('alert')).toHaveTextContent('No "suggestions" list')
  })
})
