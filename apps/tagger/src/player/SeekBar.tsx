import { useState, type FormEvent, type PointerEvent } from 'react'
import { usePlayer } from './PlayerContext'
import { formatClock, parseClock } from './time'

/** Seconds at a pointer's position along an element, clamped to the video. */
function timeAtPointer(event: PointerEvent<HTMLElement>, duration: number): number {
  const box = event.currentTarget.getBoundingClientRect()
  if (box.width <= 0) return 0
  const share = Math.min(1, Math.max(0, (event.clientX - box.left) / box.width))
  return share * duration
}

/** A bar over the whole video, like a video site's, and a field to jump to a time. */
export function SeekBar() {
  const { src, currentTime, duration, seek } = usePlayer()
  const [hover, setHover] = useState<{ seconds: number; left: number } | null>(null)
  const [goTo, setGoTo] = useState('')
  const [error, setError] = useState<string | null>(null)
  const ready = src !== null && duration > 0

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const ms = parseClock(goTo)
    if (ms === null) {
      setError('Use m:ss or h:mm:ss, for example 4:20.')
      return
    }
    if (ms / 1000 > duration) {
      setError(`The video is ${formatClock(duration)} long.`)
      return
    }
    setError(null)
    setGoTo('')
    seek(ms / 1000)
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="relative">
        <input
          type="range"
          aria-label="Seek"
          aria-valuetext={`${formatClock(currentTime)} of ${formatClock(duration)}`}
          min={0}
          max={ready ? duration : 0}
          step="any"
          value={ready ? Math.min(currentTime, duration) : 0}
          disabled={!ready}
          onChange={(event) => seek(Number(event.currentTarget.value))}
          // Give the keyboard back to Space and the arrows after a click or drag.
          onPointerUp={(event) => event.currentTarget.blur()}
          onPointerMove={(event) =>
            setHover({
              seconds: timeAtPointer(event, duration),
              left: event.clientX - event.currentTarget.getBoundingClientRect().left,
            })
          }
          onPointerLeave={() => setHover(null)}
          className="h-2 w-full cursor-pointer accent-neutral-100 disabled:cursor-default disabled:opacity-40"
        />
        {ready && hover && (
          <span
            aria-hidden="true"
            className="pointer-events-none absolute -top-7 -translate-x-1/2 rounded bg-neutral-800 px-1.5 py-0.5 font-mono text-xs text-neutral-100 tabular-nums"
            style={{ left: hover.left }}
          >
            {formatClock(hover.seconds)}
          </span>
        )}
      </div>

      <form onSubmit={submit} className="flex flex-wrap items-center gap-2 text-sm">
        <label className="flex items-center gap-2 text-neutral-300">
          Go to
          <input
            type="text"
            inputMode="numeric"
            value={goTo}
            placeholder="m:ss"
            disabled={!ready}
            onChange={(event) => {
              setGoTo(event.currentTarget.value)
              setError(null)
            }}
            className="w-24 rounded border border-neutral-700 bg-neutral-900 px-2 py-1 font-mono disabled:opacity-40"
          />
        </label>
        <button
          type="submit"
          disabled={!ready}
          className="rounded border border-neutral-700 px-3 py-1 hover:bg-neutral-800 disabled:opacity-40 disabled:hover:bg-transparent"
        >
          Go
        </button>
        {error && (
          <span role="alert" className="text-xs text-red-400">
            {error}
          </span>
        )}
      </form>
    </div>
  )
}
