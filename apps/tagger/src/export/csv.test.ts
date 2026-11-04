import { sampleStats } from '../test/fightStats'
import { makeTag } from '../test/tag'
import { csvCell, statsCsv, TAG_COLUMNS, tagsCsv, toCsv } from './csv'
import tagSchema from '../../../../shared/schema/tag.schema.json'

const lines = (csv: string) => csv.trimEnd().split('\r\n')

describe('csvCell', () => {
  it('leaves plain values alone', () => {
    expect(csvCell('kick')).toBe('kick')
    expect(csvCell(61250)).toBe('61250')
    expect(csvCell(0.5)).toBe('0.5')
  })

  it('writes null as an empty cell, never 0', () => {
    expect(csvCell(null)).toBe('')
  })

  it('quotes commas, quotes, and line breaks', () => {
    expect(csvCell('a,b')).toBe('"a,b"')
    expect(csvCell('say "hi"')).toBe('"say ""hi"""')
    expect(csvCell('two\nlines')).toBe('"two\nlines"')
  })

  it('stops text from running as a spreadsheet formula', () => {
    expect(csvCell('=HYPERLINK("x")')).toBe(`"'=HYPERLINK(""x"")"`)
    expect(csvCell('+1')).toBe("'+1")
    expect(csvCell('@user')).toBe("'@user")
  })

  it('does not touch negative numbers', () => {
    expect(csvCell(-1)).toBe('-1')
  })
})

describe('toCsv', () => {
  it('ends every line with CRLF', () => {
    expect(toCsv(['a', 'b'], [[1, null]])).toBe('a,b\r\n1,\r\n')
  })
})

describe('tagsCsv', () => {
  it('uses exactly the tag schema fields, in schema order', () => {
    expect([...TAG_COLUMNS]).toEqual(tagSchema.required)
    expect(lines(tagsCsv([]))[0]).toBe(tagSchema.required.join(','))
  })

  it('writes confirmed tags in video order and leaves out the rest', () => {
    const csv = tagsCsv([
      makeTag({ id: 'b', timestamp_ms: 9000 }),
      makeTag({ id: 'p', status: 'pending', source: 'cv', confidence: 0.8 }),
      makeTag({ id: 'a', timestamp_ms: 1000 }),
      makeTag({ id: 'r', status: 'rejected' }),
    ])
    const rows = lines(csv).slice(1)
    expect(rows).toHaveLength(2)
    expect(rows[0]).toBe(
      'a,fight-1,1,1000,red,kick,landed,body,human,,confirmed,analyst,2026-11-04T10:00:00Z',
    )
    expect(rows[1]?.startsWith('b,')).toBe(true)
  })

  it('keeps the confidence of a confirmed CV tag', () => {
    const csv = tagsCsv([makeTag({ source: 'cv', confidence: 0.82 })])
    expect(lines(csv)[1]).toContain(',cv,0.82,confirmed,')
  })
})

describe('statsCsv', () => {
  const csv = statsCsv(sampleStats())
  const rows = lines(csv)

  it('has a long-format header', () => {
    expect(rows[0]).toBe('group,item,fighter,metric,value')
  })

  it('copies totals and rates from the API', () => {
    expect(rows).toContain('totals,all,red,attempts,3')
    expect(rows).toContain(`totals,all,red,accuracy,${2 / 3}`)
    expect(rows).toContain('fight,all,both,fight_time_s,360')
  })

  it('writes undefined values as empty cells', () => {
    expect(rows).toContain('totals,all,blue,accuracy,')
    expect(rows).toContain('target_landed,head,blue,share,')
  })

  it('flags partial rounds', () => {
    expect(rows).toContain('round,1,both,partial,0')
    expect(rows).toContain('round,2,both,partial,1')
  })

  it('includes per-round splits, weapon groups, and both target bases', () => {
    expect(rows).toContain('round,1,red,attempts,2')
    expect(rows).toContain('weapon_group,punch,red,attempts,2')
    expect(rows).toContain('target_attempted,head,red,count,2')
  })

  it('lists the provisional rules', () => {
    expect(rows).toContain(
      'provisional_rule,,,rule,Every strike in a combination is its own attempt.',
    )
  })
})
