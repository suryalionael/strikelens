import type { Corner, Tag } from '../api/types'
import { formatTime } from '../player/time'

interface Props {
  reviewing: boolean
  /** The current suggestion with the analyst's edits applied, or null. */
  current: Tag | null
  pendingCount: number
  progress: { reviewed: number; total: number }
  minConfidence: number
  /** The round being reviewed, or null for the whole fight. */
  round: number | null
  /** Rounds that have suggestions, for the picker. */
  rounds: readonly number[]
  onRound: (round: number | null) => void
  busy: boolean
  onToggle: () => void
  onMinConfidence: (value: number) => void
  onStep: (direction: 1 | -1) => void
  onConfirm: () => void
  onReject: () => void
}

const CORNER_TEXT: Record<Corner, string> = { red: 'text-red-400', blue: 'text-blue-400' }

/** A field of the current suggestion, or a word saying it still has to be set. */
function Field({ value, name }: { value: string | null; name: string }) {
  return value === null ? <span className="text-amber-300">{name}?</span> : <>{value}</>
}
const button =
  'rounded border border-neutral-700 px-2 py-1 text-xs hover:bg-neutral-800 disabled:opacity-40'

/** Review CV suggestions: step through them, confirm, or reject (#26). */
export function ReviewBar({
  reviewing,
  current,
  pendingCount,
  progress,
  minConfidence,
  round,
  rounds,
  onRound,
  busy,
  onToggle,
  onMinConfidence,
  onStep,
  onConfirm,
  onReject,
}: Props) {
  return (
    <div
      role="region"
      aria-label="Suggestions"
      className="flex flex-col gap-2 rounded border border-amber-900/60 bg-amber-950/20 p-3 text-sm"
    >
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          aria-pressed={reviewing}
          onClick={onToggle}
          className={`${button} aria-pressed:bg-amber-200 aria-pressed:text-neutral-950`}
        >
          {reviewing ? 'Stop reviewing' : 'Review suggestions'}
        </button>
        <label className="flex items-center gap-2 text-xs text-neutral-400">
          Round
          <select
            value={round ?? 'all'}
            onChange={(event) => {
              const value = event.currentTarget.value
              onRound(value === 'all' ? null : Number(value))
            }}
            className="rounded border border-neutral-700 bg-neutral-900 px-1 py-0.5 text-neutral-100"
          >
            {rounds.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
            <option value="all">All</option>
          </select>
        </label>
        <span aria-label="Review progress" className="text-xs text-neutral-300">
          {round === null ? 'Whole fight' : `Round ${round}`}: {progress.reviewed} of{' '}
          {progress.total} reviewed · {pendingCount} pending
        </span>
        <label className="ml-auto flex items-center gap-2 text-xs text-neutral-400">
          Min confidence
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={minConfidence}
            onChange={(event) => onMinConfidence(Number(event.currentTarget.value))}
            className="w-24 accent-amber-300"
          />
          <span className="w-8 font-mono tabular-nums">{minConfidence.toFixed(2)}</span>
        </label>
      </div>

      {reviewing && (
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className={button} onClick={() => onStep(-1)}>
            ← Previous (Shift+Tab)
          </button>
          <button type="button" className={button} onClick={() => onStep(1)}>
            Next (Tab) →
          </button>
          {current ? (
            <>
              <p aria-label="Current suggestion" className="text-xs">
                <span className={CORNER_TEXT[current.fighter]}>{current.fighter}</span>{' '}
                <Field value={current.weapon} name="weapon" /> ·{' '}
                <Field value={current.outcome} name="outcome" /> ·{' '}
                <Field value={current.target} name="target" /> at{' '}
                {formatTime(current.timestamp_ms / 1000)}
                {current.confidence !== null && (
                  <span className="text-neutral-500">
                    {' '}
                    · confidence {current.confidence.toFixed(2)}
                  </span>
                )}
              </p>
              <button
                type="button"
                className={`${button} ml-auto border-emerald-700 text-emerald-200`}
                disabled={busy}
                onClick={onConfirm}
              >
                Confirm (Enter)
              </button>
              <button
                type="button"
                className={`${button} border-red-800 text-red-300`}
                disabled={busy}
                onClick={onReject}
              >
                Reject (X)
              </button>
            </>
          ) : (
            <p className="text-xs text-neutral-400">
              Press Tab to jump to the next suggestion. Set what is still blank (the motion model
              guesses no weapon) with the usual keys, then Enter to confirm or X to reject.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
