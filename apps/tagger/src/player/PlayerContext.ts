import { createContext, useContext } from 'react'
import type { Player } from './usePlayerState'

export const PlayerContext = createContext<Player | null>(null)

/** Player state and controls for any component inside PlayerProvider. */
export function usePlayer(): Player {
  const player = useContext(PlayerContext)
  if (!player) throw new Error('usePlayer must be used inside PlayerProvider')
  return player
}
