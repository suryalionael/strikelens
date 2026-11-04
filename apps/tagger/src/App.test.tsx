import { render, screen } from '@testing-library/react'
import { api } from './api/client'
import App from './App'

describe('App', () => {
  it('renders the player and the fight panel', async () => {
    vi.spyOn(api, 'listFighters').mockResolvedValue([])
    vi.spyOn(api, 'listFights').mockResolvedValue([])
    render(<App />)
    expect(screen.getByRole('heading', { name: 'StrikeLens' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Video player' })).toBeInTheDocument()
    expect(await screen.findByRole('form', { name: 'New fight' })).toBeInTheDocument()
    vi.restoreAllMocks()
  })
})
