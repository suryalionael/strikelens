import { makeTag } from '../test/tag'
import { HISTORY_LIMIT, record, undoStep, upsert, without, type TagAction } from './history'

describe('record', () => {
  it('appends actions in order', () => {
    const a: TagAction = { kind: 'create', tag: makeTag({ id: 'a' }) }
    const b: TagAction = { kind: 'delete', tag: makeTag({ id: 'b' }) }
    expect(record(record([], a), b)).toEqual([a, b])
  })

  it('keeps at least 20 steps and drops the oldest past the limit', () => {
    expect(HISTORY_LIMIT).toBeGreaterThanOrEqual(20)
    let history: TagAction[] = []
    for (let i = 0; i < HISTORY_LIMIT + 5; i++) {
      history = record(history, { kind: 'create', tag: makeTag({ id: `t${i}` }) })
    }
    expect(history).toHaveLength(HISTORY_LIMIT)
    expect(history[0]).toMatchObject({ tag: { id: 't5' } })
  })
})

describe('undoStep', () => {
  it('undoes a create by deleting the tag', () => {
    const tag = makeTag()
    expect(undoStep({ kind: 'create', tag })).toEqual({ op: 'delete', tag })
  })

  it('undoes a delete by restoring the same tag', () => {
    const tag = makeTag()
    expect(undoStep({ kind: 'delete', tag })).toEqual({ op: 'restore', tag })
  })

  it('undoes an edit by reverting to the tag before it', () => {
    const before = makeTag({ weapon: 'jab' })
    const after = makeTag({ weapon: 'cross' })
    expect(undoStep({ kind: 'edit', before, after })).toEqual({ op: 'revert', to: before })
  })
})

describe('list helpers', () => {
  it('replaces a tag in place or adds it', () => {
    const list = [makeTag({ id: 'a' }), makeTag({ id: 'b' })]
    expect(upsert(list, makeTag({ id: 'a', weapon: 'jab' }))[0]?.weapon).toBe('jab')
    expect(upsert(list, makeTag({ id: 'c' })).map((t) => t.id)).toEqual(['a', 'b', 'c'])
  })

  it('removes a tag by id', () => {
    expect(without([makeTag({ id: 'a' }), makeTag({ id: 'b' })], 'a').map((t) => t.id)).toEqual([
      'b',
    ])
  })
})
