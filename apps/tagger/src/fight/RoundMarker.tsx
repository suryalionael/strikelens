import { useRef, useState, type ChangeEvent } from 'react'
import { api, fightInput } from '../api/client'
import type { Fight, Segment } from '../api/types'
import { usePlayer } from '../player/PlayerContext'
import { formatTime } from '../player/time'
import {
  completedRounds,
  endRound,
  nextMark,
  removeLastRound,
  roundErrors,
  setRoundTime,
  startRound,
  type RoundDraft,
} from './rounds'
import { parseRoundSuggestions, type RoundSuggestion } from './roundSuggestions'
import { button, primaryButton } from './styles'
import { TimeField } from './TimeField'

type SaveState = { kind: 'saved' } | { kind: 'saving' } | { kind: 'failed'; message: string }

interface Props {
  fight: Fight
  /** Round marks, including an open round. Owned by the app so tagging can read them. */
  rounds: RoundDraft[]
  /** The segments to save alongside, so a round save never undoes a segment save. */
  segments: Segment[]
  onRoundsChange: (rounds: RoundDraft[]) => void
  onSaved: (fight: Fight) => void
}

export function RoundMarker({ fight, rounds, segments, onRoundsChange, onSaved }: Props) {
  const { currentTime, src, seek } = usePlayer()
  const [save, setSave] = useState<SaveState>({ kind: 'saved' })
  const [suggestions, setSuggestions] = useState<RoundSuggestion[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  // Only the newest save may update the status, in case responses arrive out of order.
  const latestSave = useRef(0)
  // What was last sent, not what was last saved, so a change made while a save is
  // in flight (for example undoing it) is still sent.
  const lastSent = useRef<string | null>(JSON.stringify(fight.rounds))

  const nowMs = Math.round(currentTime * 1000)
  const errors = roundErrors(rounds, fight.scheduled_rounds)
  const mark = nextMark(rounds, fight.scheduled_rounds)
  const openRound = rounds.find((r) => r.end_ms === null)

  const apply = (next: RoundDraft[]) => {
    onRoundsChange(next)
    if (roundErrors(next, fight.scheduled_rounds).length > 0) return
    const toSave = completedRounds(next)
    if (JSON.stringify(toSave) === lastSent.current) return
    lastSent.current = JSON.stringify(toSave)
    const id = ++latestSave.current
    setSave({ kind: 'saving' })
    api
      .replaceFight(fight.id, { ...fightInput(fight), rounds: toSave, segments })
      .then((saved) => {
        if (id !== latestSave.current) return
        setSave({ kind: 'saved' })
        onSaved(saved)
      })
      .catch((error: unknown) => {
        if (id !== latestSave.current) return
        lastSent.current = null
        setSave({ kind: 'failed', message: error instanceof Error ? error.message : String(error) })
      })
  }

  const loadSuggestions = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.currentTarget.files?.[0]
    event.currentTarget.value = ''
    if (!file) return
    file
      .text()
      .then((text) => {
        setSuggestions(parseRoundSuggestions(text))
        setLoadError(null)
      })
      .catch((error: unknown) => {
        setLoadError(error instanceof Error ? error.message : String(error))
      })
  }

  const acceptSuggestions = (list: RoundSuggestion[]) => {
    apply(list.map(({ number, start_ms, end_ms }) => ({ number, start_ms, end_ms })))
    setSuggestions(null)
  }

  const status =
    errors.length > 0
      ? 'Not saved. Fix the problems below.'
      : save.kind === 'saving'
        ? 'Saving…'
        : save.kind === 'failed'
          ? `Not saved: ${save.message}`
          : openRound
            ? `Round ${openRound.number} is open. It is saved when you mark its end.`
            : rounds.length === 0
              ? 'No rounds marked yet.'
              : 'All rounds saved.'

  return (
    <section aria-label="Rounds" className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold">Rounds</h3>
        <span className="text-xs text-neutral-500">
          {completedRounds(rounds).length} of {fight.scheduled_rounds} marked
        </span>
      </div>

      {mark ? (
        <button
          type="button"
          className={primaryButton}
          disabled={src === null}
          onClick={() =>
            apply(mark.kind === 'start' ? startRound(rounds, nowMs) : endRound(rounds, nowMs))
          }
        >
          {mark.kind === 'start' ? 'Start' : 'End'} round {mark.round} at {formatTime(currentTime)}
        </button>
      ) : (
        <p className="text-xs text-neutral-400">Every scheduled round is marked.</p>
      )}
      {src === null && (
        <p className="text-xs text-neutral-500">Open the fight video to mark rounds.</p>
      )}
      <p className="text-xs text-neutral-500">
        If the fight ends early, end the last round at the stoppage and stop there.
      </p>

      {rounds.length > 0 && (
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-neutral-500">
            <tr>
              <th className="font-normal">Round</th>
              <th className="font-normal">Start</th>
              <th className="font-normal">End</th>
            </tr>
          </thead>
          <tbody>
            {rounds.map((round) => (
              <tr key={round.number}>
                <td className="py-1">{round.number}</td>
                {(['start_ms', 'end_ms'] as const).map((field) => {
                  const value = round[field]
                  const name = field === 'start_ms' ? 'start' : 'end'
                  return (
                    <td key={field} className="py-1">
                      <div className="flex items-center gap-1">
                        <TimeField
                          key={`${round.number}-${field}-${value}`}
                          label={`Round ${round.number} ${name}`}
                          value={value}
                          onCommit={(ms) => apply(setRoundTime(rounds, round.number, field, ms))}
                        />
                        {value !== null && (
                          <button
                            type="button"
                            className="px-1 text-xs text-neutral-400 hover:text-neutral-100 disabled:opacity-40"
                            disabled={src === null}
                            title="Jump the video to this time"
                            aria-label={`Go to round ${round.number} ${name}`}
                            onClick={() => seek(value / 1000)}
                          >
                            ▶
                          </button>
                        )}
                      </div>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {errors.length > 0 && (
        <ul role="alert" className="list-inside list-disc text-xs text-red-400">
          {errors.map((error) => (
            <li key={error.message}>{error.message}</li>
          ))}
        </ul>
      )}

      <div className="flex items-center justify-between gap-2">
        <p aria-live="polite" className="text-xs text-neutral-400">
          {status}
        </p>
        {rounds.length > 0 && (
          <button type="button" className={button} onClick={() => apply(removeLastRound(rounds))}>
            Remove round {rounds.length}
          </button>
        )}
      </div>

      <div className="flex flex-col gap-2 border-t border-neutral-800 pt-3">
        <label className="flex flex-col gap-1 text-xs text-neutral-400">
          Load round suggestions (round-suggestions.json from strikelens-cv ingest)
          <input
            type="file"
            accept="application/json,.json"
            className="text-xs text-neutral-300 file:mr-2 file:rounded file:border file:border-neutral-700 file:bg-transparent file:px-2 file:py-1 file:text-neutral-200"
            onChange={loadSuggestions}
          />
        </label>
        {loadError && (
          <p role="alert" className="text-xs text-red-400">
            {loadError}
          </p>
        )}
        {suggestions !== null && suggestions.length === 0 && (
          <p className="text-xs text-neutral-500">
            No rounds found from the scoreboard. Mark them by hand.
          </p>
        )}
        {suggestions !== null && suggestions.length > 0 && (
          <>
            <ul aria-label="Suggested rounds" className="flex flex-col gap-1 text-xs">
              {suggestions.map((s) => (
                <li key={s.number} className="flex flex-wrap items-baseline gap-x-2">
                  <span className="font-medium">
                    Round {s.number}: {formatTime(s.start_ms / 1000)} to{' '}
                    {formatTime(s.end_ms / 1000)}
                  </span>
                  {s.partial && <span className="text-amber-400">check the end</span>}
                  <button
                    type="button"
                    className="text-neutral-400 hover:text-neutral-100 disabled:opacity-40"
                    disabled={src === null}
                    aria-label={`Watch the start of suggested round ${s.number}`}
                    onClick={() => seek(s.start_ms / 1000)}
                  >
                    ▶ start
                  </button>
                  <button
                    type="button"
                    className="text-neutral-400 hover:text-neutral-100 disabled:opacity-40"
                    disabled={src === null}
                    aria-label={`Watch the end of suggested round ${s.number}`}
                    onClick={() => seek(s.end_ms / 1000)}
                  >
                    ▶ end
                  </button>
                  {s.reason && <span className="w-full text-neutral-500">{s.reason}</span>}
                </li>
              ))}
            </ul>
            <div className="flex gap-2">
              <button
                type="button"
                className={primaryButton}
                onClick={() => acceptSuggestions(suggestions)}
              >
                {rounds.length > 0 ? 'Replace the marked rounds with these' : 'Use these rounds'}
              </button>
              <button type="button" className={button} onClick={() => setSuggestions(null)}>
                Dismiss
              </button>
            </div>
          </>
        )}
      </div>
    </section>
  )
}
