import {
  formatClock,
  formatTime,
  frameIndex,
  jumpTime,
  parseClock,
  parseTime,
  stepFrameTime,
} from './time'

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

describe('parseTime', () => {
  it.each([
    ['00:00.000', 0],
    ['01:01.234', 61234],
    ['1:05', 65000],
    ['62:05.001', 3725001],
    ['90', 90000],
    ['3.5', 3500],
    [' 02:00.5 ', 120500],
  ])('parses %s as %i ms', (text, ms) => {
    expect(parseTime(text)).toBe(ms)
  })

  it.each(['', 'abc', '1:60', '-1', '1:2:3', '00:00.1234'])('rejects %j', (text) => {
    expect(parseTime(text)).toBeNull()
  })

  it('round-trips with formatTime', () => {
    expect(parseTime(formatTime(61.234))).toBe(61234)
  })
})

describe('formatClock', () => {
  it.each([
    [0, '0:00'],
    [4.9, '0:04'],
    [260, '4:20'],
    [3599, '59:59'],
    [3600, '1:00:00'],
    [3725, '1:02:05'],
    [Number.NaN, '0:00'],
  ])('formats %s s as %s', (seconds, text) => {
    expect(formatClock(seconds)).toBe(text)
  })
})

describe('parseClock', () => {
  it.each([
    ['4:20', 260_000],
    ['04:20', 260_000],
    ['260', 260_000],
    ['1:02:05', 3_725_000],
    ['0:59.5', 59_500],
    [' 2:00 ', 120_000],
  ])('reads %s as %s ms', (text, ms) => {
    expect(parseClock(text)).toBe(ms)
  })

  it.each(['', 'abc', '4:60', '1:60:00', '4:20:', '-1', '4.20.1'])('rejects %j', (text) => {
    expect(parseClock(text)).toBeNull()
  })
})

describe('jumpTime', () => {
  it('jumps forward and back', () => {
    expect(jumpTime(100, 30, 600)).toBe(130)
    expect(jumpTime(100, -5, 600)).toBe(95)
  })

  it('stops at the start and the end of the video', () => {
    expect(jumpTime(3, -5, 600)).toBe(0)
    expect(jumpTime(590, 30, 600)).toBe(600)
  })
})
