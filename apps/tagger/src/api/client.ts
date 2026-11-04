import type { Fight, FightInput, Fighter } from './types'

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// FastAPI returns { detail: string } for most errors and { detail: [...] } for
// validation errors. Turn either into one readable line.
function describe(body: unknown, status: number): string {
  if (typeof body === 'object' && body !== null && 'detail' in body) {
    const { detail } = body
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((item: unknown) =>
          typeof item === 'object' && item !== null && 'msg' in item ? String(item.msg) : '',
        )
        .filter(Boolean)
        .join('; ')
    }
  }
  return `Request failed (${status})`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(0, `Cannot reach the API at ${API_URL}. Is it running?`)
  }
  const body: unknown = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, describe(body, response.status))
  // The API validates its responses against the same schemas these types mirror.
  return body as T
}

export const api = {
  listFighters: () => request<Fighter[]>('/fighters'),
  createFighter: (name: string) =>
    request<Fighter>('/fighters', { method: 'POST', body: JSON.stringify({ name }) }),
  listFights: () => request<Fight[]>('/fights'),
  createFight: (fight: FightInput) =>
    request<Fight>('/fights', { method: 'POST', body: JSON.stringify(fight) }),
  replaceFight: (id: string, fight: FightInput) =>
    request<Fight>(`/fights/${id}`, { method: 'PUT', body: JSON.stringify(fight) }),
}

export function fightInput(fight: Fight): FightInput {
  const { id, ...rest } = fight
  void id
  return rest
}
