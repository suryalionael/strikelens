import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('renders the StrikeLens heading', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'StrikeLens' })).toBeInTheDocument()
  })
})
