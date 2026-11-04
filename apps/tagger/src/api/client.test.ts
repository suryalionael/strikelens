import { ApiError, api, fightInput } from './client'
import type { Fight } from './types'

function respond(status: number, body: unknown) {
  return vi
    .spyOn(globalThis, 'fetch')
    .mockResolvedValue(new Response(status === 204 ? null : JSON.stringify(body), { status }))
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('api client', () => {
  it('sends JSON and returns the parsed body', async () => {
    const fetchMock = respond(201, { id: 'f1', name: 'Red Fighter' })
    await expect(api.createFighter('Red Fighter')).resolves.toEqual({
      id: 'f1',
      name: 'Red Fighter',
    })
    const [url, init] = fetchMock.mock.calls[0] ?? []
    expect(url).toBe('http://localhost:8000/fighters')
    expect(init?.method).toBe('POST')
    expect(init?.body).toBe('{"name":"Red Fighter"}')
  })

  it('turns a detail string into an ApiError', async () => {
    respond(404, { detail: 'fight not found' })
    await expect(api.listFights()).rejects.toEqual(new ApiError(404, 'fight not found'))
  })

  it('joins validation messages', async () => {
    respond(422, { detail: [{ msg: 'Value error, round 2 ends before it starts' }, { msg: 'x' }] })
    await expect(api.listFights()).rejects.toThrow('Value error, round 2 ends before it starts; x')
  })

  it('explains when the API is not running', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(api.listFighters()).rejects.toThrow('Cannot reach the API')
  })

  it('drops the id when building a PUT body', () => {
    const fight = { id: 'x', event: 'E' } as Fight
    expect(fightInput(fight)).toEqual({ event: 'E' })
  })
})

describe('tag edits', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('patches only the changed fields', async () => {
    const fetchMock = respond(200, { id: 't1' })
    await api.updateTag('f1', 't1', { weapon: 'jab' })
    const [url, init] = fetchMock.mock.calls[0] ?? []
    expect(url).toBe('http://localhost:8000/fights/f1/tags/t1')
    expect(init?.method).toBe('PATCH')
    expect(init?.body).toBe('{"weapon":"jab"}')
  })

  it('deletes a tag and accepts the empty 204 reply', async () => {
    const fetchMock = respond(204, null)
    await expect(api.deleteTag('f1', 't1')).resolves.toBeNull()
    expect(fetchMock.mock.calls[0]?.[1]?.method).toBe('DELETE')
  })

  it('restores a tag with its id and time, without fight_id in the body', async () => {
    const fetchMock = respond(201, { id: 't1' })
    await api.restoreTag({
      id: 't1',
      fight_id: 'f1',
      round: 1,
      timestamp_ms: 5,
      fighter: 'red',
      weapon: 'jab',
      outcome: 'landed',
      target: 'head',
      source: 'human',
      confidence: null,
      status: 'confirmed',
      created_by: 'analyst',
      created_at: '2026-11-04T10:00:00Z',
    })
    const [url, init] = fetchMock.mock.calls[0] ?? []
    expect(url).toBe('http://localhost:8000/fights/f1/tags')
    const body: unknown = JSON.parse(String(init?.body))
    expect(body).toMatchObject({ id: 't1', created_at: '2026-11-04T10:00:00Z' })
    expect(body).not.toHaveProperty('fight_id')
  })
})
