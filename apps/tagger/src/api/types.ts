// Mirrors shared/schema/*.json. Field names stay snake_case to match the API.

export type Corner = 'red' | 'blue'

export interface Fighter {
  id: string
  name: string
  nickname: string | null
  gym: string | null
  country: string | null
}

export interface Round {
  number: number
  start_ms: number
  end_ms: number
}

export interface FightResult {
  winner: 'red' | 'blue' | 'draw' | 'no_contest' | null
  method: string | null
  round: number | null
}

export interface Fight {
  id: string
  event: string
  date: string
  red_fighter_id: string
  blue_fighter_id: string
  weight_class: string | null
  scheduled_rounds: number
  video_file: string | null
  rounds: Round[]
  result: FightResult | null
}

export type FightInput = Omit<Fight, 'id'>
