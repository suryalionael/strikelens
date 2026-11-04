import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Corner, Fight, Tag } from '../api/types'
import type { RoundDraft } from '../fight/rounds'
import { usePlayer } from '../player/PlayerContext'
import { formatTime } from '../player/time'
import { isFormControl } from '../player/keys'
import { planEdit, revertPatch, type TagEdit } from './edits'
import { applyKey, INITIAL_TAGGING, type TaggingState } from './engine'
import { record, undoStep, upsert, without, type TagAction } from './history'
import { actionFor, DEFAULT_HOTKEYS, hotkeyAction, keyFor, type HotkeyAction } from './hotkeys'
import { TagEditor } from './TagEditor'
import { buildTag } from './tags'
import { Timeline } from './Timeline'

// There are no user accounts yet. Every human tag is attributed to this name.
export const ANALYST_NAME = 'analyst'

const RECENT_COUNT = 8
/** How long the confirmation for the last saved tag stays on screen. */
export const CONFIRM_MS = 3000

type Message = { kind: 'info' | 'error'; text: string }

interface Props {
  fight: Fight | null
  rounds: RoundDraft[]
  /** Called after any tag is created, changed, deleted, or undone, so stats refresh. */
  onTagsChanged?: () => void
}

const FIELDS = {
  weapon: ['jab', 'cross', 'hook', 'uppercut', 'kick', 'knee', 'elbow', 'teep'],
  outcome: ['landed', 'missed', 'blocked'],
  target: ['head', 'body', 'legs'],
} as const
type Field = keyof typeof FIELDS

const CORNER_LABEL: Record<Corner, string> = { red: 'Red', blue: 'Blue' }
const CORNER_TEXT: Record<Corner, string> = { red: 'text-red-400', blue: 'text-blue-400' }
const CORNER_ACTIVE: Record<Corner, string> = {
  red: 'aria-pressed:border-red-500 aria-pressed:bg-red-600 aria-pressed:text-white',
  blue: 'aria-pressed:border-blue-500 aria-pressed:bg-blue-600 aria-pressed:text-white',
}

const option =
  'rounded border border-neutral-700 px-2 py-1 text-xs text-neutral-300 hover:bg-neutral-800'
const optionActive =
  'aria-pressed:border-neutral-100 aria-pressed:bg-neutral-100 aria-pressed:text-neutral-950'

function describe(tag: Pick<Tag, 'fighter' | 'weapon' | 'outcome' | 'target'>): string {
  return [CORNER_LABEL[tag.fighter], tag.weapon, tag.outcome, tag.target].join(' ')
}

function describeAt(tag: Tag): string {
  return `${describe(tag)} at ${formatTime(tag.timestamp_ms / 1000)}`
}

const reason = (error: unknown) => (error instanceof Error ? error.message : String(error))

function isUndoKey(event: KeyboardEvent): boolean {
  return (
    (event.ctrlKey || event.metaKey) &&
    !event.shiftKey &&
    !event.altKey &&
    event.key.toLowerCase() === 'z' &&
    // In a text field, Ctrl+Z belongs to the field.
    !isFormControl(event.target)
  )
}

/** Mount with `key={fight id}` so a new fight starts with a clean draft and tag list. */
export function TagPanel({ fight, rounds, onTagsChanged }: Props) {
  const { src, videoRef } = usePlayer()
  const [tagging, setTagging] = useState<TaggingState>(INITIAL_TAGGING)
  // Handlers read the latest state from here, so two quick keys never see a stale render.
  const taggingRef = useRef<TaggingState>(INITIAL_TAGGING)
  const [tags, setTags] = useState<Tag[]>([])
  const [message, setMessage] = useState<Message | null>(null)
  const [confirmed, setConfirmed] = useState<Tag | null>(null)
  // The undo stack is not drawn, so it lives in a ref and is read and written at the
  // moment of each change. A Cmd+Z pressed right after the last one then always
  // sees the current stack, never one a render behind.
  const historyRef = useRef<TagAction[]>([])
  const remember = (action: TagAction) => {
    historyRef.current = record(historyRef.current, action)
  }
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  // Blocks a second edit or undo until the first reaches the server.
  const busyRef = useRef(false)
  const fightId = fight?.id ?? null
  const ready = fightId !== null && src !== null

  useEffect(() => {
    if (fightId === null) return
    let cancelled = false
    api
      .listTags(fightId)
      .then((loaded) => {
        if (!cancelled) setTags(loaded)
      })
      .catch((error: unknown) => {
        if (!cancelled) setMessage({ kind: 'error', text: String(error) })
      })
    return () => {
      cancelled = true
    }
  }, [fightId])

  useEffect(() => {
    if (confirmed === null) return
    const timer = setTimeout(() => setConfirmed(null), CONFIRM_MS)
    return () => clearTimeout(timer)
  }, [confirmed])

  /** One path for keys and clicks, so both behave the same. */
  const handle = (action: HotkeyAction) => {
    if (fightId === null || src === null) return
    const now_ms = Math.round((videoRef.current?.currentTime ?? 0) * 1000)
    const result = applyKey(taggingRef.current, action, now_ms)
    taggingRef.current = result.state
    setTagging(result.state)
    if (!result.complete) return

    const built = buildTag(result.complete, rounds, ANALYST_NAME)
    if (!built.ok) {
      setMessage({ kind: 'error', text: built.error })
      return
    }
    const label = `${describe(built.tag)} at ${formatTime(built.tag.timestamp_ms / 1000)}, round ${built.tag.round}`
    setMessage({ kind: 'info', text: `Saving ${label}…` })
    api
      .createTag(fightId, built.tag)
      .then((saved) => {
        setTags((list) => upsert(list, saved))
        remember({ kind: 'create', tag: saved })
        setMessage(null)
        setConfirmed(saved)
        onTagsChanged?.()
      })
      .catch((error: unknown) => {
        setMessage({ kind: 'error', text: `Not saved (${label}): ${reason(error)}` })
      })
  }

  /**
   * Run one server change at a time, then refresh the stats. `work` returns the
   * state updates to apply. The lock is released in the same step as those updates,
   * so the next Ctrl+Z after the screen changes is never refused as "still saving".
   */
  const run = (work: () => Promise<() => void>) => {
    if (busyRef.current) {
      setMessage({ kind: 'info', text: 'Still saving the last change. Try again in a moment.' })
      return
    }
    busyRef.current = true
    setBusy(true)
    const release = () => {
      busyRef.current = false
      setBusy(false)
    }
    work().then(
      (apply) => {
        release()
        apply()
        onTagsChanged?.()
      },
      (error: unknown) => {
        release()
        setMessage({ kind: 'error', text: reason(error) })
      },
    )
  }

  const editTag = (tag: Tag, edit: TagEdit) => {
    if (fightId === null) return
    const plan = planEdit(tag, edit, rounds)
    if (!plan.ok) {
      setMessage({ kind: 'error', text: plan.error })
      return
    }
    run(async () => {
      const saved = await api.updateTag(fightId, tag.id, plan.patch)
      return () => {
        setTags((list) => upsert(list, saved))
        remember({ kind: 'edit', before: tag, after: saved })
        setMessage({ kind: 'info', text: `Changed to ${describeAt(saved)}.` })
      }
    })
  }

  const deleteTag = (tag: Tag) => {
    if (fightId === null) return
    run(async () => {
      await api.deleteTag(fightId, tag.id)
      return () => {
        setTags((list) => without(list, tag.id))
        remember({ kind: 'delete', tag })
        setSelectedId(null)
        setMessage({ kind: 'info', text: `Deleted ${describeAt(tag)}. Ctrl+Z / Cmd+Z undoes.` })
      }
    })
  }

  const undo = () => {
    if (fightId === null) return
    if (busyRef.current) {
      // The change in flight is not in the history yet, so wait for it.
      setMessage({ kind: 'info', text: 'Still saving the last change. Try again in a moment.' })
      return
    }
    const last = historyRef.current[historyRef.current.length - 1]
    if (!last) {
      setMessage({ kind: 'info', text: 'Nothing to undo.' })
      return
    }
    const step = undoStep(last)
    run(async () => {
      let show: () => void
      if (step.op === 'delete') {
        await api.deleteTag(fightId, step.tag.id)
        show = () => {
          setTags((list) => without(list, step.tag.id))
          setSelectedId((id) => (id === step.tag.id ? null : id))
          setMessage({ kind: 'info', text: `Undid: removed ${describeAt(step.tag)}.` })
        }
      } else if (step.op === 'restore') {
        const saved = await api.restoreTag(step.tag)
        show = () => {
          setTags((list) => upsert(list, saved))
          setMessage({ kind: 'info', text: `Undid: put back ${describeAt(saved)}.` })
        }
      } else {
        const saved = await api.updateTag(fightId, step.to.id, revertPatch(step.to))
        show = () => {
          setTags((list) => upsert(list, saved))
          setMessage({ kind: 'info', text: `Undid: back to ${describeAt(saved)}.` })
        }
      }
      return () => {
        show()
        // Drop the step only once the server agreed, so a failed undo can be retried.
        historyRef.current = historyRef.current.slice(0, -1)
      }
    })
  }

  // The key listener is added once; it always calls the newest `handle` and `undo`.
  // A layout effect refreshes them before React yields, so a key pressed right after
  // the screen changes never reaches a handler from the render before.
  const handleRef = useRef(handle)
  const undoRef = useRef(undo)
  useLayoutEffect(() => {
    handleRef.current = handle
    undoRef.current = undo
  })

  useEffect(() => {
    if (!ready) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (isUndoKey(event)) {
        event.preventDefault()
        undoRef.current()
        return
      }
      const action = hotkeyAction(event, DEFAULT_HOTKEYS)
      if (!action) return
      event.preventDefault()
      handleRef.current(action)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [ready])

  const { fighter, draft } = tagging
  const selected = tags.find((t) => t.id === selectedId) ?? null
  const recent = [...tags].sort((a, b) => b.timestamp_ms - a.timestamp_ms).slice(0, RECENT_COUNT)

  return (
    <section
      aria-label="Tagging"
      className="flex flex-col gap-3 rounded border border-neutral-800 p-4"
    >
      <div className="flex items-baseline justify-between">
        <h2 className="font-semibold">Tagging</h2>
        <span className="text-xs text-neutral-500">{tags.length} tags</span>
      </div>

      {!fightId && (
        <p className="text-sm text-neutral-400">Open or create a fight to start tagging.</p>
      )}
      {fightId && !src && (
        <p className="text-sm text-neutral-400">Open the fight video to start tagging.</p>
      )}

      {ready && (
        <Timeline tags={tags} rounds={rounds} selectedId={selectedId} onSelect={setSelectedId} />
      )}

      {ready && selected && (
        <TagEditor
          key={selected.id}
          tag={selected}
          busy={busy}
          onEdit={(edit) => editTag(selected, edit)}
          onDelete={() => deleteTag(selected)}
          onClose={() => setSelectedId(null)}
        />
      )}

      {ready && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <div role="group" aria-label="Fighter" className="flex gap-1">
              {(['red', 'blue'] as const).map((corner) => (
                <button
                  key={corner}
                  type="button"
                  aria-pressed={fighter === corner}
                  aria-keyshortcuts={keyFor('fighter', corner) ?? undefined}
                  onClick={() => {
                    const action = actionFor('fighter', corner)
                    if (action) handle(action)
                  }}
                  className={`${option} text-sm ${CORNER_ACTIVE[corner]}`}
                >
                  <kbd aria-hidden className="mr-1 font-mono text-xs opacity-70">
                    {keyFor('fighter', corner)}
                  </kbd>
                  {CORNER_LABEL[corner]} corner
                </button>
              ))}
            </div>
            <p aria-label="Current tag" className="text-sm text-neutral-400">
              {fighter ? (
                <span className={CORNER_TEXT[fighter]}>{CORNER_LABEL[fighter]}</span>
              ) : (
                'No fighter'
              )}
              {' · '}
              {draft.weapon ?? '—'} · {draft.outcome ?? '—'} · {draft.target ?? '—'}
              <span className="ml-2 text-neutral-500">
                {draft.started_ms === null
                  ? 'Press a key or click to start a tag'
                  : `at ${formatTime(draft.started_ms / 1000)}`}
              </span>
            </p>
            {draft.started_ms !== null && (
              <button
                type="button"
                className="ml-auto text-xs text-neutral-400 underline hover:text-neutral-100"
                onClick={() => handle({ field: 'clear' })}
              >
                Clear (Esc)
              </button>
            )}
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            {(Object.keys(FIELDS) as Field[]).map((field) => (
              <div key={field} role="group" aria-label={field} className="flex flex-col gap-1">
                <span className="text-xs text-neutral-500 capitalize">{field}</span>
                <div className="flex flex-wrap gap-1">
                  {FIELDS[field].map((value) => {
                    const action = actionFor(field, value)
                    return (
                      <button
                        key={value}
                        type="button"
                        aria-pressed={draft[field] === value}
                        aria-keyshortcuts={keyFor(field, value) ?? undefined}
                        disabled={action === null}
                        onClick={() => {
                          if (action) handle(action)
                        }}
                        className={`${option} ${optionActive}`}
                      >
                        <kbd aria-hidden className="mr-1 font-mono opacity-60">
                          {keyFor(field, value)}
                        </kbd>
                        {value}
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <div role="status" aria-live="polite" className="min-h-5 text-xs">
        {confirmed && (
          <span className="rounded bg-emerald-900/60 px-2 py-1 text-emerald-200">
            Saved:{' '}
            <span className={CORNER_TEXT[confirmed.fighter]}>
              {CORNER_LABEL[confirmed.fighter]}
            </span>{' '}
            {confirmed.weapon} {confirmed.outcome} {confirmed.target} at{' '}
            {formatTime(confirmed.timestamp_ms / 1000)}, round {confirmed.round}
          </span>
        )}
        {message && (
          <span className={message.kind === 'error' ? 'text-red-400' : 'text-neutral-400'}>
            {message.text}
          </span>
        )}
      </div>

      {recent.length > 0 && (
        <table className="w-full text-sm">
          <caption className="text-left text-xs text-neutral-500">Latest tags</caption>
          <thead className="text-left text-xs text-neutral-500">
            <tr>
              <th className="font-normal">Time</th>
              <th className="font-normal">Round</th>
              <th className="font-normal">Fighter</th>
              <th className="font-normal">Strike</th>
              <th className="font-normal">
                <span className="sr-only">Edit</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {recent.map((tag) => (
              <tr
                key={tag.id}
                aria-selected={tag.id === selectedId}
                className="aria-selected:bg-neutral-800"
              >
                <td className="font-mono tabular-nums">{formatTime(tag.timestamp_ms / 1000)}</td>
                <td>{tag.round}</td>
                <td className={CORNER_TEXT[tag.fighter]}>{CORNER_LABEL[tag.fighter]}</td>
                <td>{[tag.weapon, tag.outcome, tag.target].join(' · ')}</td>
                <td className="text-right">
                  <button
                    type="button"
                    className="text-xs text-neutral-400 underline hover:text-neutral-100"
                    aria-label={`Edit ${describeAt(tag)}`}
                    onClick={() => setSelectedId(tag.id)}
                  >
                    Edit
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
