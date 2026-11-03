import { PlayerProvider } from './player/PlayerProvider'
import { VideoPlayer } from './player/VideoPlayer'

function App() {
  return (
    <PlayerProvider>
      <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 p-6">
        <h1 className="text-2xl font-bold tracking-tight">StrikeLens</h1>
        <VideoPlayer />
      </main>
    </PlayerProvider>
  )
}

export default App
