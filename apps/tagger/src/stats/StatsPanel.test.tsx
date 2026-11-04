import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { api } from '../api/client'
import type { Fight, Fighter } from '../api/types'
import { sampleStats } from '../test/fightStats'
import { StatsPanel } from './StatsPanel'

const FIGHT = {
  id: 'fight-1',
  red_fighter_id: 'red-1',
  blue_fighter_id: 'blue-1',
  rounds: [],
} as unknown as Fight

const fighter = (id: string, name: string): Fighter => ({
  id,
  name,
  nickname: null,
  gym: null,
  country: null,
})

beforeEach(() => {
  vi.spyOn(api, 'getStats').mockResolvedValue(sampleStats())
  vi.spyOn(api, 'getFighter').mockImplementation((id) =>
    Promise.resolve(id === 'red-1' ? fighter(id, 'Red Fighter') : fighter(id, 'Blue Fighter')),
  )
})

afterEach(() => {
  vi.restoreAllMocks()
})

const headline = async () => screen.findByRole('table', { name: 'Headline stats' })

describe('StatsPanel', () => {
  it('shows nothing before a fight is open', () => {
    const { container } = render(<StatsPanel fight={null} refreshKey={0} />)
    expect(container).toBeEmptyDOMElement()
    expect(api.getStats).not.toHaveBeenCalled()
  })

  it('shows the headline numbers for both fighters', async () => {
    render(<StatsPanel fight={FIGHT} refreshKey={0} />)
    const table = await headline()
    await waitFor(() => expect(table).toHaveTextContent('Red: Red Fighter'))
    expect(table).toHaveTextContent('Blue: Blue Fighter')
    const row = (label: string) => within(table).getByRole('row', { name: new RegExp(`^${label}`) })
    expect(row('Attempts')).toHaveTextContent('Attempts30')
    expect(row('Accuracy')).toHaveTextContent('Accuracy66.7%—')
    expect(row('Strikes per minute')).toHaveTextContent('Strikes per minute0.50.0')
    expect(table).toHaveTextContent('Fight time 6:00 over 2 marked rounds')
  })

  it('shows a dash for undefined values, never 0%', async () => {
    render(<StatsPanel fight={FIGHT} refreshKey={0} />)
    const table = await headline()
    expect(within(table).queryByText('0.0%')).toBeNull()
    expect(within(table).getByText('—')).toBeInTheDocument()
  })

  it('lists the provisional rules', async () => {
    render(<StatsPanel fight={FIGHT} refreshKey={0} />)
    const note = await screen.findByRole('complementary', { name: 'Provisional definitions' })
    expect(note).toHaveTextContent('Every strike in a combination is its own attempt.')
  })

  it('marks a partial round', async () => {
    render(<StatsPanel fight={FIGHT} refreshKey={0} />)
    const rounds = await screen.findByRole('table', { name: 'Attempts per round table' })
    expect(rounds).toHaveTextContent('R2 (partial)')
    expect(screen.getByText(/A round marked partial ended early/)).toBeInTheDocument()
  })

  it('warns about confirmed tags outside every round', async () => {
    vi.mocked(api.getStats).mockResolvedValue(sampleStats({ uncounted_tags: 2 }))
    render(<StatsPanel fight={FIGHT} refreshKey={0} />)
    expect(
      await screen.findByText('2 confirmed tags are outside every marked round and not counted.'),
    ).toBeInTheDocument()
  })

  it('switches the target chart between landed and all attempts', async () => {
    render(<StatsPanel fight={FIGHT} refreshKey={0} />)
    await screen.findByText('Target distribution (landed strikes)')
    const landed = screen.getByRole('table', { name: 'Target distribution (landed strikes) table' })
    expect(within(landed).getByRole('row', { name: /^head/ })).toHaveTextContent('head150.0%')

    fireEvent.click(screen.getByRole('button', { name: 'All attempts' }))
    const all = screen.getByRole('table', { name: 'Target distribution (all attempts) table' })
    expect(within(all).getByRole('row', { name: /^head/ })).toHaveTextContent('head266.7%')
  })

  it('shows weapon groups with counts and shares', async () => {
    render(<StatsPanel fight={FIGHT} refreshKey={0} />)
    const mix = await screen.findByRole('table', { name: 'Weapon mix (attempts) table' })
    expect(within(mix).getByRole('row', { name: /^punch/ })).toHaveTextContent('punch2066.7%00—')
  })

  it('refetches when a tag is saved', async () => {
    const { rerender } = render(<StatsPanel fight={FIGHT} refreshKey={0} />)
    await headline()
    expect(api.getStats).toHaveBeenCalledTimes(1)
    rerender(<StatsPanel fight={FIGHT} refreshKey={1} />)
    await waitFor(() => expect(api.getStats).toHaveBeenCalledTimes(2))
  })

  it('refetches when round marks change', async () => {
    const { rerender } = render(<StatsPanel fight={FIGHT} refreshKey={0} />)
    await headline()
    const moved = { ...FIGHT, rounds: [{ number: 1, start_ms: 0, end_ms: 1000 }] }
    rerender(<StatsPanel fight={moved} refreshKey={0} />)
    await waitFor(() => expect(api.getStats).toHaveBeenCalledTimes(2))
  })

  it('keeps showing the last stats and says when a refresh fails', async () => {
    const { rerender } = render(<StatsPanel fight={FIGHT} refreshKey={0} />)
    await headline()
    vi.mocked(api.getStats).mockRejectedValueOnce(new Error('API down'))
    rerender(<StatsPanel fight={FIGHT} refreshKey={1} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Stats not updated: API down')
    expect(screen.getByRole('table', { name: 'Headline stats' })).toBeInTheDocument()
  })
})
