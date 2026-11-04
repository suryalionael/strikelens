import { useState } from 'react'
import type { Corner, Tag } from '../api/types'
import { TimeField } from '../fight/TimeField'
import { usePlayer } from '../player/PlayerContext'
import type { TagEdit } from './edits'

const CORNER_LABEL: Record<Corner, string> = { red: 'Red', blue: 'Blue' }

interface Choice {
  label: string
  edit: TagEdit
  isCurrent: (tag: Tag) => boolean
}

const ROWS: { field: string; choices: Choice[] }[] = [
  {
    field: 'fighter',
    choices: (['red', 'blue'] as const).map((v) => ({
      label: CORNER_LABEL[v],
      edit: { fighter: v },
      isCurrent: (t) => t.fighter === v,
    })),
  },
  {
    field: 'weapon',
    choices: (['jab', 'cross', 'hook', 'uppercut', 'kick', 'knee', 'elbow', 'teep'] as const).map(
      (v) => ({ label: v, edit: { weapon: v }, isCurrent: (t) => t.weapon === v }),
    ),
  },
  {
    field: 'outcome',
    choices: (['landed', 'missed', 'blocked'] as const).map((v) => ({
      label: v,
      edit: { outcome: v },
      isCurrent: (t) => t.outcome === v,
    })),
  },
  {
    field: 'target',
    choices: (['head', 'body', 'legs'] as const).map((v) => ({
      label: v,
      edit: { target: v },
      isCurrent: (t) => t.target === v,
    })),
  },
]

const option =
  'rounded border border-neutral-700 px-2 py-0.5 text-xs text-neutral-300 hover:bg-neutral-800 aria-pressed:border-neutral-100 aria-pressed:bg-neutral-100 aria-pressed:text-neutral-950 disabled:opacity-40'

interface Props {
  tag: Tag
  busy: boolean
  onEdit: (edit: TagEdit) => void
  onDelete: () => void
  onClose: () => void
}

/** Change or delete one saved tag. Every change is saved at once and can be undone. */
export function TagEditor({ tag, busy, onEdit, onDelete, onClose }: Props) {
  const { videoRef, seek } = usePlayer()
  const [confirmDelete, setConfirmDelete] = useState(false)

  return (
    <section
      aria-label="Edit tag"
      className="flex flex-col gap-2 rounded border border-neutral-700 bg-neutral-900 p-3"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">
          Edit tag <span className="font-normal text-neutral-400">· round {tag.round}</span>
        </h3>
        <button
          type="button"
          className="text-xs text-neutral-400 underline hover:text-neutral-100"
          onClick={onClose}
        >
          Close
        </button>
      </div>

      {ROWS.map(({ field, choices }) => (
        <div
          key={field}
          role="group"
          aria-label={`Edit ${field}`}
          className="flex items-center gap-2"
        >
          <span className="w-14 text-xs text-neutral-500 capitalize">{field}</span>
          <div className="flex flex-wrap gap-1">
            {choices.map((choice) => {
              const current = choice.isCurrent(tag)
              return (
                <button
                  key={choice.label}
                  type="button"
                  disabled={busy}
                  aria-pressed={current}
                  className={option}
                  onClick={() => {
                    if (!current) onEdit(choice.edit)
                  }}
                >
                  {choice.label}
                </button>
              )
            })}
          </div>
        </div>
      ))}

      <div className="flex flex-wrap items-center gap-2">
        <span className="w-14 text-xs text-neutral-500">Time</span>
        <TimeField
          key={tag.timestamp_ms}
          label="Tag time"
          value={tag.timestamp_ms}
          onCommit={(ms) => onEdit({ timestamp_ms: ms })}
        />
        <button
          type="button"
          disabled={busy}
          className={option}
          // Read the video itself, like tagging does; the displayed time can lag a frame.
          onClick={() =>
            onEdit({ timestamp_ms: Math.round((videoRef.current?.currentTime ?? 0) * 1000) })
          }
        >
          Set to video time
        </button>
        <button type="button" className={option} onClick={() => seek(tag.timestamp_ms / 1000)}>
          Go to tag
        </button>
      </div>

      <div className="flex items-center gap-2 pt-1">
        {confirmDelete ? (
          <>
            <span className="text-xs text-neutral-300">Delete this tag?</span>
            <button
              type="button"
              disabled={busy}
              className="rounded bg-red-700 px-2 py-0.5 text-xs text-white hover:bg-red-600"
              onClick={() => {
                setConfirmDelete(false)
                onDelete()
              }}
            >
              Delete
            </button>
            <button type="button" className={option} onClick={() => setConfirmDelete(false)}>
              Keep
            </button>
          </>
        ) : (
          <button
            type="button"
            disabled={busy}
            className="rounded border border-red-900 px-2 py-0.5 text-xs text-red-300 hover:bg-red-950"
            onClick={() => setConfirmDelete(true)}
          >
            Delete tag…
          </button>
        )}
        <span className="ml-auto text-xs text-neutral-500">Ctrl+Z / Cmd+Z undoes</span>
      </div>
    </section>
  )
}
