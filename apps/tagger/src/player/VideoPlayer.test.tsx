import { act, fireEvent, render, screen } from '@testing-library/react'
import { PlayerProvider } from './PlayerProvider'
import { usePlayer } from './PlayerContext'
import { VideoPlayer } from './VideoPlayer'

// jsdom has no media playback or object URLs, so stub the parts the player uses.
let paused = true
beforeEach(() => {
  paused = true
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:fight')
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
  vi.spyOn(HTMLMediaElement.prototype, 'paused', 'get').mockImplementation(() => paused)
  vi.spyOn(HTMLMediaElement.prototype, 'duration', 'get').mockReturnValue(10)
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockImplementation(function (
    this: HTMLMediaElement,
  ) {
    paused = false
    this.dispatchEvent(new Event('play'))
    return Promise.resolve()
  })
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(function (
    this: HTMLMediaElement,
  ) {
    if (paused) return
    paused = true
    this.dispatchEvent(new Event('pause'))
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

function TimeProbe() {
  const { currentTime, playing, rate } = usePlayer()
  return <p data-testid="probe">{`${currentTime.toFixed(4)} ${playing} ${rate}`}</p>
}

function setup() {
  render(
    <PlayerProvider>
      <VideoPlayer />
      <TimeProbe />
    </PlayerProvider>,
  )
  const input = screen.getByLabelText('Fight video')
  fireEvent.change(input, {
    target: { files: [new File(['x'], 'fight.mp4', { type: 'video/mp4' })] },
  })
  const video = document.querySelector('video')
  if (!video) throw new Error('video not rendered')
  fireEvent(video, new Event('loadedmetadata'))
  return video
}

describe('VideoPlayer', () => {
  it('asks for a local file before showing a video', () => {
    render(
      <PlayerProvider>
        <VideoPlayer />
      </PlayerProvider>,
    )
    expect(screen.getByText(/never uploaded/)).toBeInTheDocument()
    expect(document.querySelector('video')).toBeNull()
    expect(screen.getByRole('button', { name: 'Play' })).toBeDisabled()
  })

  it('plays the picked file from an object URL, not an upload', () => {
    const video = setup()
    expect(URL.createObjectURL).toHaveBeenCalledOnce()
    expect(video.getAttribute('src')).toBe('blob:fight')
    expect(screen.getByLabelText('Current time')).toHaveTextContent('00:00.000 / 00:10.000')
  })

  it('toggles play and pause with Space', () => {
    setup()
    fireEvent.keyDown(window, { key: ' ' })
    expect(screen.getByTestId('probe')).toHaveTextContent('true')
    expect(screen.getByRole('button', { name: 'Pause' })).toBeInTheDocument()
    fireEvent.keyDown(window, { key: ' ' })
    expect(screen.getByTestId('probe')).toHaveTextContent('false')
  })

  it('ignores Space while typing in a form control', () => {
    setup()
    fireEvent.keyDown(screen.getByRole('combobox'), { key: ' ' })
    expect(HTMLMediaElement.prototype.play).not.toHaveBeenCalled()
  })

  it('steps one frame with the arrow keys and pauses first', () => {
    const video = setup()
    fireEvent.keyDown(window, { key: ' ' })
    fireEvent.keyDown(window, { key: 'ArrowRight' })
    expect(paused).toBe(true)
    expect(video.currentTime).toBeCloseTo(1.5 / 30)
    fireEvent.keyDown(window, { key: 'ArrowRight' })
    expect(video.currentTime).toBeCloseTo(2.5 / 30)
    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    expect(video.currentTime).toBeCloseTo(1.5 / 30)
  })

  it('uses the chosen frame rate for stepping', () => {
    const video = setup()
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '25' } })
    fireEvent.keyDown(window, { key: 'ArrowRight' })
    expect(video.currentTime).toBeCloseTo(1.5 / 25)
  })

  it('shares time with other components through usePlayer', () => {
    const video = setup()
    act(() => {
      video.currentTime = 61.234
      fireEvent(video, new Event('seeked'))
    })
    expect(screen.getByTestId('probe')).toHaveTextContent('61.2340')
    expect(screen.getByLabelText('Current time')).toHaveTextContent('01:01.234')
  })

  it('sets the playback speed', () => {
    const video = setup()
    for (const rate of ['0.25x', '0.5x', '1x', '1.5x', '2x']) {
      expect(screen.getByRole('button', { name: rate })).toBeInTheDocument()
    }
    fireEvent.click(screen.getByRole('button', { name: '0.25x' }))
    expect(video.playbackRate).toBe(0.25)
    expect(screen.getByRole('button', { name: '0.25x' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('probe')).toHaveTextContent('0.25')
  })

  it('throws a clear error when usePlayer is used outside the provider', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    expect(() => render(<TimeProbe />)).toThrow('usePlayer must be used inside PlayerProvider')
  })
})
