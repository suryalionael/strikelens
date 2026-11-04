import { useCallback, useEffect, useRef, useState } from 'react'
import { DEFAULT_FRAME_RATE, stepFrameTime, type PlaybackRate } from './time'

export interface Player {
  /** Object URL of the loaded local file, or null before a file is picked. */
  src: string | null
  fileName: string | null
  /** Seconds from the start of the video. */
  currentTime: number
  /** Seconds, or 0 before metadata loads. */
  duration: number
  playing: boolean
  rate: PlaybackRate
  fps: number
  loadFile: (file: File) => void
  togglePlay: () => void
  pause: () => void
  seek: (seconds: number) => void
  stepFrame: (direction: 1 | -1) => void
  setRate: (rate: PlaybackRate) => void
  setFps: (fps: number) => void
  videoRef: React.RefObject<HTMLVideoElement | null>
  /** Spread onto the <video> element so the state follows the element. */
  videoHandlers: Pick<
    React.VideoHTMLAttributes<HTMLVideoElement>,
    'onPlay' | 'onPause' | 'onTimeUpdate' | 'onSeeked' | 'onLoadedMetadata' | 'onDurationChange'
  >
}

/** Owns the <video> element and mirrors its state into React. Use via PlayerProvider. */
export function usePlayerState(): Player {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [src, setSrc] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [rate, setRateState] = useState<PlaybackRate>(1)
  const [fps, setFps] = useState(DEFAULT_FRAME_RATE)

  // The file stays in the browser. Free the object URL when it is replaced.
  useEffect(() => {
    if (!src) return
    return () => URL.revokeObjectURL(src)
  }, [src])

  // timeupdate fires only about 4 times a second, too coarse for a ms clock.
  useEffect(() => {
    if (!playing) return
    let id = 0
    const tick = () => {
      const video = videoRef.current
      if (video) setCurrentTime(video.currentTime)
      id = requestAnimationFrame(tick)
    }
    id = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(id)
  }, [playing])

  const loadFile = useCallback((file: File) => {
    setSrc(URL.createObjectURL(file))
    setFileName(file.name)
    setCurrentTime(0)
    setDuration(0)
    setPlaying(false)
  }, [])

  const togglePlay = useCallback(() => {
    const video = videoRef.current
    if (!video || !src) return
    if (video.paused) {
      video.play().catch((error: unknown) => {
        console.error('Video could not play', error)
      })
    } else {
      video.pause()
    }
  }, [src])

  const pause = useCallback(() => {
    videoRef.current?.pause()
  }, [])

  const seek = useCallback(
    (seconds: number) => {
      const video = videoRef.current
      if (!video || !src) return
      video.currentTime = Math.min(Math.max(0, seconds), video.duration || 0)
    },
    [src],
  )

  // Stepping pauses first: a step is meaningless while the video moves.
  const stepFrame = useCallback(
    (direction: 1 | -1) => {
      const video = videoRef.current
      if (!video || !src || !video.duration) return
      video.pause()
      video.currentTime = stepFrameTime(video.currentTime, fps, direction, video.duration)
    },
    [src, fps],
  )

  const setRate = useCallback((next: PlaybackRate) => {
    setRateState(next)
    const video = videoRef.current
    if (video) video.playbackRate = next
  }, [])

  const syncTime = () => {
    const video = videoRef.current
    if (video) setCurrentTime(video.currentTime)
  }

  const videoHandlers: Player['videoHandlers'] = {
    onPlay: () => setPlaying(true),
    onPause: () => {
      setPlaying(false)
      syncTime()
    },
    onTimeUpdate: syncTime,
    onSeeked: syncTime,
    onLoadedMetadata: (event) => {
      // A new source resets playbackRate, so apply the chosen speed again.
      event.currentTarget.playbackRate = rate
      setDuration(event.currentTarget.duration)
      syncTime()
    },
    onDurationChange: (event) => setDuration(event.currentTarget.duration),
  }

  return {
    src,
    fileName,
    currentTime,
    duration,
    playing,
    rate,
    fps,
    loadFile,
    togglePlay,
    pause,
    seek,
    stepFrame,
    setRate,
    setFps,
    videoRef,
    videoHandlers,
  }
}
