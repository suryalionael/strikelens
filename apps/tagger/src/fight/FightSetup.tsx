import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Fight, Fighter } from '../api/types'
import { usePlayer } from '../player/PlayerContext'
import { FightForm } from './FightForm'
import type { RoundDraft } from './rounds'
import { RoundMarker } from './RoundMarker'
import { button, input, label } from './styles'

interface Props {
  fight: Fight | null
  rounds: RoundDraft[]
  /** A different fight was opened, created, or closed (null). */
  onFightOpen: (fight: Fight | null) => void
  /** The open fight was saved with new rounds. */
  onFightSaved: (fight: Fight) => void
  onRoundsChange: (rounds: RoundDraft[]) => void
}

export function FightSetup({ fight, rounds, onFightOpen, onFightSaved, onRoundsChange }: Props) {
  const { fileName } = usePlayer()
  const [fighters, setFighters] = useState<Fighter[]>([])
  const [fights, setFights] = useState<Fight[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([api.listFighters(), api.listFights()])
      .then(([loadedFighters, loadedFights]) => {
        if (cancelled) return
        setFighters(loadedFighters)
        setFights(loadedFights)
      })
      .catch((error: unknown) => {
        if (!cancelled) setLoadError(error instanceof Error ? error.message : String(error))
      })
    return () => {
      cancelled = true
    }
  }, [])

  const nameOf = (id: string) => fighters.find((f) => f.id === id)?.name ?? 'Unknown fighter'

  const remember = (saved: Fight) =>
    setFights((list) => [saved, ...list.filter((f) => f.id !== saved.id)])

  if (fight) {
    return (
      <div className="flex flex-col gap-4">
        <header className="flex items-start justify-between gap-2">
          <div>
            <h2 className="font-semibold">{fight.event}</h2>
            <p className="text-sm">
              <span className="text-red-400">{nameOf(fight.red_fighter_id)}</span>
              <span className="text-neutral-500"> vs </span>
              <span className="text-blue-400">{nameOf(fight.blue_fighter_id)}</span>
            </p>
            <p className="text-xs text-neutral-500">
              {fight.date} · {fight.scheduled_rounds} rounds scheduled
              {fight.weight_class ? ` · ${fight.weight_class}` : ''}
            </p>
            {fight.video_file && fileName && fight.video_file !== fileName && (
              <p className="mt-1 text-xs text-amber-400">
                This fight was set up with {fight.video_file}, but {fileName} is open.
              </p>
            )}
          </div>
          <button type="button" className={button} onClick={() => onFightOpen(null)}>
            Switch fight
          </button>
        </header>
        <RoundMarker
          key={fight.id}
          fight={fight}
          rounds={rounds}
          onRoundsChange={onRoundsChange}
          onSaved={(saved) => {
            remember(saved)
            onFightSaved(saved)
          }}
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="font-semibold">Fight</h2>
      {loadError && (
        <p role="alert" className="text-xs text-red-400">
          {loadError}
        </p>
      )}
      {fights.length > 0 && (
        <label className={label}>
          Open a saved fight
          <select
            className={input}
            value=""
            onChange={(event) => {
              const chosen = fights.find((f) => f.id === event.currentTarget.value)
              if (chosen) onFightOpen(chosen)
            }}
          >
            <option value="">Choose a fight</option>
            {fights.map((f) => (
              <option key={f.id} value={f.id}>
                {f.date} · {f.event}: {nameOf(f.red_fighter_id)} vs {nameOf(f.blue_fighter_id)}
              </option>
            ))}
          </select>
        </label>
      )}
      <h3 className="text-sm font-semibold">New fight</h3>
      <FightForm
        fighters={fighters}
        videoFile={fileName}
        onFighterCreated={(fighter) => setFighters((list) => [...list, fighter])}
        onCreated={(created) => {
          remember(created)
          onFightOpen(created)
        }}
      />
    </div>
  )
}
