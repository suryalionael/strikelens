import { useEffect } from 'react'
import { playerKeyAction } from './keys'
import { usePlayer } from './PlayerContext'
import { FRAME_RATES, PLAYBACK_RATES, formatTime, frameIndex } from './time'

const button =
  'rounded border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800 disabled:opacity-40 disabled:hover:bg-transparent'

export function VideoPlayer() {
  const {
    src,
    currentTime,
    duration,
    playing,
    rate: currentRate,
    fps: currentFps,
    loadFile,
    togglePlay,
    stepFrame,
    setRate,
    setFps,
    videoRef,
    videoHandlers,
  } = usePlayer()
  const loaded = src !== null

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const action = playerKeyAction(event)
      if (!action) return
      // Stop Space scrolling the page or clicking a focused button.
      event.preventDefault()
      if (action === 'toggle-play') togglePlay()
      else stepFrame(action === 'step-back' ? -1 : 1)
    }
    // Browsers click a focused button on Space keyup, so block that too.
    const onKeyUp = (event: KeyboardEvent) => {
      if (playerKeyAction(event) === 'toggle-play') event.preventDefault()
    }
    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
    }
  }, [togglePlay, stepFrame])

  return (
    <section aria-label="Video player" className="flex flex-col gap-3">
      <label className="flex items-center gap-3 text-sm text-neutral-300">
        <span>Fight video</span>
        <input
          type="file"
          accept="video/*"
          className="text-sm file:mr-3 file:rounded file:border-0 file:bg-neutral-800 file:px-3 file:py-1.5 file:text-neutral-100"
          onChange={(event) => {
            const file = event.currentTarget.files?.[0]
            if (file) loadFile(file)
          }}
        />
      </label>

      <div className="flex aspect-video items-center justify-center overflow-hidden rounded bg-black">
        {loaded ? (
          <video
            ref={videoRef}
            src={src}
            className="h-full w-full"
            preload="auto"
            {...videoHandlers}
          />
        ) : (
          <p className="text-sm text-neutral-500">
            Pick a video file. It stays on this computer and is never uploaded.
          </p>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className={button}
          disabled={!loaded}
          onClick={() => stepFrame(-1)}
          aria-label="Previous frame"
        >
          ←
        </button>
        <button type="button" className={`${button} w-20`} disabled={!loaded} onClick={togglePlay}>
          {playing ? 'Pause' : 'Play'}
        </button>
        <button
          type="button"
          className={button}
          disabled={!loaded}
          onClick={() => stepFrame(1)}
          aria-label="Next frame"
        >
          →
        </button>

        <output aria-label="Current time" className="ml-2 font-mono text-sm tabular-nums">
          {formatTime(currentTime)}
          <span className="text-neutral-500"> / {formatTime(duration)}</span>
        </output>
        <span className="font-mono text-xs text-neutral-500 tabular-nums">
          frame {frameIndex(currentTime, currentFps)}
        </span>

        <div role="group" aria-label="Playback speed" className="ml-auto flex">
          {PLAYBACK_RATES.map((rate) => (
            <button
              key={rate}
              type="button"
              aria-pressed={currentRate === rate}
              onClick={() => setRate(rate)}
              className="border border-neutral-700 px-2.5 py-1.5 text-sm first:rounded-l last:rounded-r hover:bg-neutral-800 aria-pressed:bg-neutral-100 aria-pressed:text-neutral-950 [&:not(:first-child)]:-ml-px"
            >
              {rate}x
            </button>
          ))}
        </div>

        <label className="flex items-center gap-2 text-sm text-neutral-300">
          Frame rate
          <select
            value={currentFps}
            onChange={(event) => setFps(Number(event.currentTarget.value))}
            className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1.5"
          >
            {FRAME_RATES.map((fps) => (
              <option key={fps} value={fps}>
                {fps} fps
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className="text-xs text-neutral-500">
        Space plays and pauses. ← and → step one frame. Set the frame rate to match the file.
      </p>
    </section>
  )
}
