import { useState } from 'react'
import type { Fight } from './api/types'
import { FightSetup } from './fight/FightSetup'
import type { RoundDraft } from './fight/rounds'
import { PlayerProvider } from './player/PlayerProvider'
import { VideoPlayer } from './player/VideoPlayer'
import { TagPanel } from './tagging/TagPanel'

function App() {
  const [fight, setFight] = useState<Fight | null>(null)
  // Round marks live here, not in the round marker, so tagging can see an open round.
  const [rounds, setRounds] = useState<RoundDraft[]>([])

  const openFight = (opened: Fight | null) => {
    setFight(opened)
    setRounds(opened?.rounds ?? [])
  }

  return (
    <PlayerProvider>
      <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 p-6">
        <h1 className="text-2xl font-bold tracking-tight">StrikeLens</h1>
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <div className="flex flex-col gap-6">
            <VideoPlayer />
            <TagPanel key={fight?.id ?? 'none'} fight={fight} rounds={rounds} />
          </div>
          <aside className="rounded border border-neutral-800 p-4">
            <FightSetup
              fight={fight}
              rounds={rounds}
              onFightOpen={openFight}
              onFightSaved={setFight}
              onRoundsChange={setRounds}
            />
          </aside>
        </div>
      </main>
    </PlayerProvider>
  )
}

export default App
