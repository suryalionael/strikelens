import {
  addSegment,
  completedSegments,
  endSegment,
  openSegment,
  removeSegment,
  segmentAt,
  segmentErrors,
  setSegmentTime,
  startSegment,
  type SegmentDraft,
} from './segments'

const replay = (start_ms: number, end_ms: number | null): SegmentDraft => ({
  kind: 'replay',
  start_ms,
  end_ms,
})

describe('segments', () => {
  it('starts and ends one segment at a time', () => {
    const started = startSegment([], 'replay', 1_000)
    expect(openSegment(started)).toEqual(replay(1_000, null))
    expect(startSegment(started, 'non_fight', 2_000)).toEqual(started)
    const ended = endSegment(started, 4_000)
    expect(ended).toEqual([replay(1_000, 4_000)])
    expect(openSegment(ended)).toBeUndefined()
  })

  it('keeps segments in video order', () => {
    const list = addSegment([replay(50_000, 60_000)], { kind: 'non_fight', start_ms: 0, end_ms: 9 })
    expect(list.map((s) => s.start_ms)).toEqual([0, 50_000])
    const moved = setSegmentTime(list, 0, 'start_ms', 70_000)
    expect(moved.map((s) => s.start_ms)).toEqual([50_000, 70_000])
  })

  it('removes by position', () => {
    expect(removeSegment([replay(0, 1), replay(5, 6)], 0)).toEqual([replay(5, 6)])
  })

  it('reports a segment that ends before it starts', () => {
    expect(segmentErrors([replay(5_000, 5_000)])).toEqual([
      'Replay at 00:05.000 ends before it starts',
    ])
  })

  it('reports overlaps, including anything after an open segment', () => {
    expect(segmentErrors([replay(0, 10_000), replay(9_000, 12_000)])).toEqual([
      'Replay at 00:09.000 overlaps replay at 00:00.000',
    ])
    expect(segmentErrors([replay(0, null), replay(9_000, 12_000)])).toHaveLength(1)
    expect(segmentErrors([replay(0, 10_000), replay(10_000, 12_000)])).toEqual([])
  })

  it('saves only finished segments, without the open one', () => {
    expect(completedSegments([replay(5, 6), replay(10, null)])).toEqual([
      { kind: 'replay', start_ms: 5, end_ms: 6 },
    ])
  })

  it('finds the segment at a time, end exclusive, open runs on', () => {
    const list = [replay(1_000, 2_000), replay(5_000, null)]
    expect(segmentAt(list, 1_000)).toBe(list[0])
    expect(segmentAt(list, 2_000)).toBeUndefined()
    expect(segmentAt(list, 99_000)).toBe(list[1])
  })
})
