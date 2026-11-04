import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Fight, Tag } from '../api/types'
import type { RoundDraft } from '../fight/rounds'
import { usePlayer } from '../player/PlayerContext'
import { formatTime } from '../player/time'
import { applyKey, INITIAL_TAGGING, type TaggingState } from './engine'
import { DEFAULT_HOTKEYS, hotkeyAction, keyFor } from './hotkeys'
import { buildTag } from './tags'

// There are no user accounts yet. Every human tag is attributed to this name.
export const ANALYST_NAME = 'analyst'

const RECENT_COUNT = 8

type Message = { kind: 'info' | 'error'; text: string }

interface Props {
  fight: Fight | null
  rounds: RoundDraft[]
}

const OPTIONS = {
  weapon: ['jab', 'cross', 'hook', 'uppercut', 'kick', 'knee', 'elbow', 'teep'],
  outcome: ['landed', 'missed', 'blocked'],
  target: ['head', 'body', 'legs'],
} as const

function describe(tag: Pick<Tag, 'fighter' | 'weapon' | 'outcome' | 'target'>): string {
  return [tag.fighter, tag.weapon, tag.outcome, tag.target].join(' ')
}

/** Mount with `key={fight id}` so a new fight starts with a clean draft and tag list. */
export function TagPanel({ fight, rounds }: Props) {
  const { src, videoRef } = usePlayer()
  const [tagging, setTagging] = useState<TaggingState>(INITIAL_TAGGING)
  // The key handler reads the latest state from here, so it never sees a stale render.
  const taggingRef = useRef<TaggingState>(INITIAL_TAGGING)
  const [tags, setTags] = useState<Tag[]>([])
  const [message, setMessage] = useState<Message | null>(null)
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
    if (fightId === null || src === null) return
    const onKeyDown = (event: KeyboardEvent) => {
      const action = hotkeyAction(event, DEFAULT_HOTKEYS)
      if (!action) return
      event.preventDefault()
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
          setTags((list) => [...list, saved])
          setMessage({ kind: 'info', text: `Saved ${label}` })
        })
        .catch((error: unknown) => {
          const reason = error instanceof Error ? error.message : String(error)
          setMessage({ kind: 'error', text: `Not saved (${label}): ${reason}` })
        })
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [fightId, src, rounds, videoRef])

  const { fighter, draft } = tagging
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
        <>
          <div aria-label="Current tag" className="flex flex-wrap items-center gap-2 text-sm">
            {(['red', 'blue'] as const).map((corner) => (
              <span
                key={corner}
                aria-current={fighter === corner}
                className={`rounded px-2 py-1 ${
                  fighter === corner
                    ? corner === 'red'
                      ? 'bg-red-600 text-white'
                      : 'bg-blue-600 text-white'
                    : 'border border-neutral-700 text-neutral-400'
                }`}
              >
                <kbd className="mr-1 font-mono text-xs opacity-70">{keyFor('fighter', corner)}</kbd>
                {corner}
              </span>
            ))}
            <span className="ml-2 text-neutral-500">
              {draft.started_ms === null
                ? 'Press a key to start a tag'
                : `Tag at ${formatTime(draft.started_ms / 1000)} · Esc to clear`}
            </span>
          </div>

          <div className="grid gap-2 sm:grid-cols-3">
            {(Object.keys(OPTIONS) as (keyof typeof OPTIONS)[]).map((field) => (
              <div key={field} role="group" aria-label={field} className="flex flex-wrap gap-1">
                {OPTIONS[field].map((value) => (
                  <span
                    key={value}
                    aria-current={draft[field] === value}
                    className="rounded border border-neutral-800 px-1.5 py-0.5 text-xs text-neutral-400 aria-current:border-neutral-100 aria-current:bg-neutral-100 aria-current:text-neutral-950"
                  >
                    <kbd className="mr-1 font-mono opacity-60">{keyFor(field, value)}</kbd>
                    {value}
                  </span>
                ))}
              </div>
            ))}
          </div>
        </>
      )}

      {message && (
        <p
          aria-live="polite"
          className={`text-xs ${message.kind === 'error' ? 'text-red-400' : 'text-neutral-400'}`}
        >
          {message.text}
        </p>
      )}

      {recent.length > 0 && (
        <table className="w-full text-sm">
          <caption className="text-left text-xs text-neutral-500">Latest tags</caption>
          <thead className="text-left text-xs text-neutral-500">
            <tr>
              <th className="font-normal">Time</th>
              <th className="font-normal">Round</th>
              <th className="font-normal">Fighter</th>
              <th className="font-normal">Strike</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((tag) => (
              <tr key={tag.id}>
                <td className="font-mono tabular-nums">{formatTime(tag.timestamp_ms / 1000)}</td>
                <td>{tag.round}</td>
                <td className={tag.fighter === 'red' ? 'text-red-400' : 'text-blue-400'}>
                  {tag.fighter}
                </td>
                <td>{[tag.weapon, tag.outcome, tag.target].join(' · ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
