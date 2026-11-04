export const PLAYBACK_RATES = [0.25, 0.5, 1, 1.5, 2] as const
export type PlaybackRate = (typeof PLAYBACK_RATES)[number]

// Browsers do not expose a video's frame rate, so the analyst picks it.
export const FRAME_RATES = [23.976, 24, 25, 29.97, 30, 50, 59.94, 60] as const
export const DEFAULT_FRAME_RATE = 30

// Small tolerance so a time that sits exactly on a frame boundary is not read
// as the previous frame because of floating point error.
const EPSILON = 1e-6

/** Format seconds as mm:ss.mmm. Minutes keep counting past 59. */
export function formatTime(seconds: number): string {
  const totalMs = Number.isFinite(seconds) && seconds > 0 ? Math.round(seconds * 1000) : 0
  const minutes = Math.floor(totalMs / 60_000)
  const secs = Math.floor((totalMs % 60_000) / 1000)
  const ms = totalMs % 1000
  return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}.${String(ms).padStart(3, '0')}`
}

/** Zero-based index of the frame shown at `seconds`. */
export function frameIndex(seconds: number, fps: number): number {
  return Math.max(0, Math.floor(seconds * fps + EPSILON))
}

/**
 * Time to seek to for the frame `direction` frames away from the one at `seconds`.
 * Seeks to the middle of the target frame, so the browser shows that frame and
 * not its neighbour. Clamped to the first and last frame of the video.
 */
export function stepFrameTime(
  seconds: number,
  fps: number,
  direction: 1 | -1,
  duration: number,
): number {
  const lastFrame = Math.max(0, Math.ceil(duration * fps - EPSILON) - 1)
  const target = Math.min(lastFrame, Math.max(0, frameIndex(seconds, fps) + direction))
  return (target + 0.5) / fps
}

/**
 * Parse mm:ss.mmm (or m:ss, or plain seconds) into milliseconds.
 * Returns null for anything else, so callers can reject bad input.
 */
export function parseTime(text: string): number | null {
  const match = /^\s*(?:(\d+):)?(\d+)(?:\.(\d{1,3}))?\s*$/.exec(text)
  if (!match) return null
  const [, minutes, seconds = '0', fraction = ''] = match
  if (minutes !== undefined && Number(seconds) >= 60) return null
  const ms = Number(fraction.padEnd(3, '0'))
  return (Number(minutes ?? 0) * 60 + Number(seconds)) * 1000 + ms
}
