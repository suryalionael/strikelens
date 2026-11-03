import { formatTime, frameIndex, stepFrameTime } from './time'

describe('formatTime', () => {
  it.each([
    [0, '00:00.000'],
    [1.5, '00:01.500'],
    [61.234, '01:01.234'],
    [599.9999, '10:00.000'],
    [3725.001, '62:05.001'],
  ])('formats %s as %s', (seconds, expected) => {
    expect(formatTime(seconds)).toBe(expected)
  })

  it('treats negative and non-finite values as zero', () => {
    expect(formatTime(-3)).toBe('00:00.000')
    expect(formatTime(Number.NaN)).toBe('00:00.000')
    expect(formatTime(Number.POSITIVE_INFINITY)).toBe('00:00.000')
  })
})

describe('frameIndex', () => {
  it('returns the frame shown at a time', () => {
    expect(frameIndex(0, 30)).toBe(0)
    expect(frameIndex(1, 30)).toBe(30)
    expect(frameIndex(1.04, 25)).toBe(26)
  })

  it('reads an exact frame boundary as the new frame despite float error', () => {
    // 0.1 * 30 is 3.0000000000000004 and 0.7 * 30 is 20.999999999999996
    expect(frameIndex(0.7, 30)).toBe(21)
  })

  it('never returns a negative frame', () => {
    expect(frameIndex(-1, 30)).toBe(0)
  })
})

describe('stepFrameTime', () => {
  const fps = 30
  const duration = 10 // 300 frames: 0 to 299

  it('steps forward to the middle of the next frame', () => {
    expect(stepFrameTime(1, fps, 1, duration)).toBeCloseTo(31.5 / fps)
  })

  it('steps back to the middle of the previous frame', () => {
    expect(stepFrameTime(1, fps, -1, duration)).toBeCloseTo(29.5 / fps)
  })

  it('lands on consecutive frames when stepping repeatedly', () => {
    let t = 0
    for (let i = 1; i <= 50; i++) {
      t = stepFrameTime(t, fps, 1, duration)
      expect(frameIndex(t, fps)).toBe(i)
    }
    for (let i = 49; i >= 0; i--) {
      t = stepFrameTime(t, fps, -1, duration)
      expect(frameIndex(t, fps)).toBe(i)
    }
  })

  it('stays on the first frame when stepping back from it', () => {
    expect(frameIndex(stepFrameTime(0, fps, -1, duration), fps)).toBe(0)
  })

  it('stays on the last frame when stepping forward from it', () => {
    const t = stepFrameTime(duration, fps, 1, duration)
    expect(frameIndex(t, fps)).toBe(299)
    expect(t).toBeLessThan(duration)
  })

  it('works with fractional frame rates', () => {
    const t = stepFrameTime(0, 29.97, 1, duration)
    expect(frameIndex(t, 29.97)).toBe(1)
  })
})
