import { useRef, useState, type ChangeEvent } from 'react'
import { api, fightInput } from '../api/client'
import type { Fight, Round } from '../api/types'
import { usePlayer } from '../player/PlayerContext'
import { formatTime } from '../player/time'
import {
  addSegment,
  completedSegments,
  endSegment,
  openSegment,
  removeSegment,
  SEGMENT_KINDS,
  SEGMENT_LABEL,
  segmentErrors,
  setSegmentTime,
  startSegment,
  type SegmentDraft,
} from './segments'
import { button, primaryButton } from './styles'
import { parseSuggestions, type Suggestion } from './suggestions'
import { TimeField } from './TimeField'

type SaveState = { kind: 'saved' } | { kind: 'saving' } | { kind: 'failed'; message: string }

interface Props {
  fight: Fight
  /** Segment marks, including an open one. Owned by the app so tagging can read them. */
  segments: SegmentDraft[]
  /** The rounds to save alongside, so a segment save never undoes a round save. */
  rounds: Round[]
  onSegmentsChange: (segments: SegmentDraft[]) => void
  onSaved: (fight: Fight) => void
}

const jump = 'px-1 text-xs text-neutral-400 hover:text-neutral-100 disabled:opacity-40'

const range = (s: { start_ms: number; end_ms: number }) =>
  `${formatTime(s.start_ms / 1000)} to ${formatTime(s.end_ms / 1000)}`

/** Mark replays and non-fight shots. Tags inside them are flagged and not counted. */
export function SegmentMarker({ fight, segments, rounds, onSegmentsChange, onSaved }: Props) {
  const { currentTime, src, seek } = usePlayer()
  const [save, setSave] = useState<SaveState>({ kind: 'saved' })
  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  // Only the newest save may update the status, in case responses arrive out of order.
  const latestSave = useRef(0)
  // What was last sent, not what was last saved, so a change made while a save is
  // in flight (for example removing the segment) is still sent.
  const lastSent = useRef<string | null>(JSON.stringify(fight.segments))

  const nowMs = Math.round(currentTime * 1000)
  const errors = segmentErrors(segments)
  const open = openSegment(segments)

  const apply = (next: SegmentDraft[]) => {
    onSegmentsChange(next)
    if (segmentErrors(next).length > 0) return
    const toSave = completedSegments(next)
    if (JSON.stringify(toSave) === lastSent.current) return
    lastSent.current = JSON.stringify(toSave)
    const id = ++latestSave.current
    setSave({ kind: 'saving' })
    api
      .replaceFight(fight.id, { ...fightInput(fight), rounds, segments: toSave })
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
        setSuggestions(parseSuggestions(text))
        setLoadError(null)
      })
      .catch((error: unknown) => {
        setLoadError(error instanceof Error ? error.message : String(error))
      })
  }

  const dismiss = (suggestion: Suggestion) =>
    setSuggestions((list) => list?.filter((s) => s !== suggestion) ?? null)

  const status =
    errors.length > 0
      ? 'Not saved. Fix the problems below.'
      : save.kind === 'saving'
        ? 'Saving…'
        : save.kind === 'failed'
          ? `Not saved: ${save.message}`
          : open
            ? `${SEGMENT_LABEL[open.kind]} is open. It is saved when you mark its end.`
            : segments.length === 0
              ? 'No segments marked.'
              : 'All segments saved.'

  return (
    <section aria-label="Segments" className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold">Replays and non-fight</h3>
        <span className="text-xs text-neutral-500">
          {completedSegments(segments).length} marked
        </span>
      </div>
      <p className="text-xs text-neutral-500">
        Mark replays and shots with no fight action (crowd, corner). Tags inside them are not
        counted.
      </p>

      {open ? (
        <button
          type="button"
          className={primaryButton}
          disabled={src === null}
          onClick={() => apply(endSegment(segments, nowMs))}
        >
          End {SEGMENT_LABEL[open.kind].toLowerCase()} at {formatTime(currentTime)}
        </button>
      ) : (
        <div className="flex gap-2">
          {SEGMENT_KINDS.map((kind) => (
            <button
              key={kind}
              type="button"
              className={`${button} flex-1`}
              disabled={src === null}
              onClick={() => apply(startSegment(segments, kind, nowMs))}
            >
              Start {SEGMENT_LABEL[kind].toLowerCase()} at {formatTime(currentTime)}
            </button>
          ))}
        </div>
      )}

      {segments.length > 0 && (
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-neutral-500">
            <tr>
              <th className="font-normal">Kind</th>
              <th className="font-normal">Start</th>
              <th className="font-normal">End</th>
              <th className="font-normal">
                <span className="sr-only">Remove</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {segments.map((segment, index) => {
              const label = SEGMENT_LABEL[segment.kind]
              const at = formatTime(segment.start_ms / 1000)
              return (
                <tr key={`${segment.kind}-${segment.start_ms}-${index}`}>
                  <td className="py-1 text-xs">{label}</td>
                  {(['start_ms', 'end_ms'] as const).map((field) => {
                    const value = segment[field]
                    const name = field === 'start_ms' ? 'start' : 'end'
                    return (
                      <td key={field} className="py-1">
                        <div className="flex items-center gap-1">
                          <TimeField
                            key={`${index}-${field}-${value}`}
                            label={`${label} at ${at} ${name}`}
                            value={value}
                            onCommit={(ms) => apply(setSegmentTime(segments, index, field, ms))}
                          />
                          {value !== null && (
                            <button
                              type="button"
                              className={jump}
                              disabled={src === null}
                              title="Jump the video to this time"
                              aria-label={`Go to ${label.toLowerCase()} at ${at} ${name}`}
                              onClick={() => seek(value / 1000)}
                            >
                              ▶
                            </button>
                          )}
                        </div>
                      </td>
                    )
                  })}
                  <td className="py-1 text-right">
                    <button
                      type="button"
                      className="text-xs text-neutral-400 underline hover:text-neutral-100"
                      aria-label={`Remove ${label.toLowerCase()} at ${at}`}
                      onClick={() => apply(removeSegment(segments, index))}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      {errors.length > 0 && (
        <ul role="alert" className="list-inside list-disc text-xs text-red-400">
          {errors.map((error) => (
            <li key={error}>{error}</li>
          ))}
        </ul>
      )}
      <p aria-live="polite" className="text-xs text-neutral-400">
        {status}
      </p>

      <div className="flex flex-col gap-2 border-t border-neutral-800 pt-3">
        <label className="flex flex-col gap-1 text-xs text-neutral-400">
          Load suggestions (segment-suggestions.json from strikelens-cv ingest)
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
          <p className="text-xs text-neutral-500">No suggestions left.</p>
        )}
        {suggestions !== null && suggestions.length > 0 && (
          <ul aria-label="Suggested segments" className="flex flex-col gap-2">
            {suggestions.map((suggestion) => {
              const label = `${SEGMENT_LABEL[suggestion.kind]} ${range(suggestion)}`
              return (
                <li
                  key={`${suggestion.start_ms}-${suggestion.end_ms}`}
                  className="flex flex-col gap-1 rounded border border-neutral-800 p-2 text-xs"
                >
                  <span>
                    Likely {label.charAt(0).toLowerCase() + label.slice(1)}
                    {suggestion.reason && (
                      <span className="text-neutral-500"> · {suggestion.reason}</span>
                    )}
                  </span>
                  <span className="flex gap-2">
                    <button
                      type="button"
                      className={jump}
                      disabled={src === null}
                      aria-label={`Go to suggested ${label.toLowerCase()}`}
                      onClick={() => seek(suggestion.start_ms / 1000)}
                    >
                      ▶ Watch
                    </button>
                    <button
                      type="button"
                      className="text-neutral-200 underline hover:text-white"
                      aria-label={`Accept ${label.toLowerCase()}`}
                      onClick={() => {
                        const { reason, ...segment } = suggestion
                        void reason
                        apply(addSegment(segments, segment))
                        dismiss(suggestion)
                      }}
                    >
                      Accept
                    </button>
                    <button
                      type="button"
                      className="text-neutral-400 underline hover:text-neutral-100"
                      aria-label={`Dismiss ${label.toLowerCase()}`}
                      onClick={() => dismiss(suggestion)}
                    >
                      Dismiss
                    </button>
                  </span>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </section>
  )
}
