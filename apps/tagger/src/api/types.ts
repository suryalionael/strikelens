// Mirrors shared/schema/*.json. Field names stay snake_case to match the API.

export type Corner = 'red' | 'blue'
export type Weapon = 'jab' | 'cross' | 'hook' | 'uppercut' | 'kick' | 'knee' | 'elbow' | 'teep'
export type Outcome = 'landed' | 'missed' | 'blocked'
export type Target = 'head' | 'body' | 'legs'
export type TagSource = 'human' | 'cv'
export type TagStatus = 'pending' | 'confirmed' | 'rejected'

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

export interface Tag {
  id: string
  fight_id: string
  round: number
  timestamp_ms: number
  fighter: Corner
  weapon: Weapon | null
  outcome: Outcome | null
  target: Target | null
  source: TagSource
  confidence: number | null
  status: TagStatus
  created_by: string
  created_at: string
}

/** What the tagger sends. The API fills in id, fight_id, and created_at. */
export type TagInput = Omit<Tag, 'id' | 'fight_id' | 'created_at'>
