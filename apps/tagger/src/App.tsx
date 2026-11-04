import { useState } from 'react'
import type { Fight } from './api/types'
import { FightSetup } from './fight/FightSetup'
import { PlayerProvider } from './player/PlayerProvider'
import { VideoPlayer } from './player/VideoPlayer'

function App() {
  const [fight, setFight] = useState<Fight | null>(null)

  return (
    <PlayerProvider>
      <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 p-6">
        <h1 className="text-2xl font-bold tracking-tight">StrikeLens</h1>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <VideoPlayer />
          <aside className="rounded border border-neutral-800 p-4">
            <FightSetup fight={fight} onFightChange={setFight} />
          </aside>
        </div>
      </main>
    </PlayerProvider>
  )
}

export default App
