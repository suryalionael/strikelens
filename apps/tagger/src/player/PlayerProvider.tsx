import type { ReactNode } from 'react'
import { PlayerContext } from './PlayerContext'
import { usePlayerState } from './usePlayerState'

export function PlayerProvider({ children }: { children: ReactNode }) {
  const player = usePlayerState()
  return <PlayerContext value={player}>{children}</PlayerContext>
}
