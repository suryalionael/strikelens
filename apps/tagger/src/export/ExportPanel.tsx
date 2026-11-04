import { useState } from 'react'
import { api } from '../api/client'
import type { Corner, Fight, FightStats } from '../api/types'
import { buildCards, DEFAULT_CREDIT, slug } from './cards'
import { statsCsv, tagsCsv } from './csv'
import { canvasToPng, downloadBlob, downloadText, renderCard } from './download'

interface Props {
  fight: Fight
  stats: FightStats
  names: Record<Corner, string>
}

const button =
  'rounded border border-neutral-700 px-3 py-1.5 text-xs text-neutral-200 hover:bg-neutral-800 disabled:opacity-40'

const message = (error: unknown) => (error instanceof Error ? error.message : String(error))

export function ExportPanel({ fight, stats, names }: Props) {
  const [credit, setCredit] = useState(DEFAULT_CREDIT)
  const [previews, setPreviews] = useState<{ name: string; url: string }[] | null>(null)
  const [status, setStatus] = useState<{ kind: 'info' | 'error'; text: string } | null>(null)
  const [working, setWorking] = useState(false)
  const base = `strikelens-${slug(fight.event)}-${fight.date}`
  const cards = () => buildCards(stats, fight, names, credit.trim() || DEFAULT_CREDIT)

  const preview = () => {
    try {
      setPreviews(
        cards().map((card) => ({ name: card.fileName, url: renderCard(card).toDataURL() })),
      )
      setStatus(null)
    } catch (error) {
      setStatus({ kind: 'error', text: message(error) })
    }
  }

  const downloadCards = async () => {
    setWorking(true)
    try {
      const all = cards()
      for (const card of all) downloadBlob(await canvasToPng(renderCard(card)), card.fileName)
      setStatus({ kind: 'info', text: `Downloaded ${all.length} cards (1080×1350 PNG).` })
    } catch (error) {
      setStatus({ kind: 'error', text: message(error) })
    } finally {
      setWorking(false)
    }
  }

  const downloadTags = async () => {
    setWorking(true)
    try {
      // Fetch fresh, so the file matches the server even if the panel is behind.
      const tags = await api.listTags(fight.id)
      downloadText(tagsCsv(tags), `${base}-tags.csv`, 'text/csv')
      const count = tags.filter((t) => t.status === 'confirmed').length
      setStatus({ kind: 'info', text: `Downloaded ${count} confirmed tags.` })
    } catch (error) {
      setStatus({ kind: 'error', text: message(error) })
    } finally {
      setWorking(false)
    }
  }

  const downloadStats = () => {
    downloadText(statsCsv(stats), `${base}-stats.csv`, 'text/csv')
    setStatus({ kind: 'info', text: 'Downloaded the stats summary.' })
  }

  return (
    <section aria-label="Export" className="flex flex-col gap-3 border-t border-neutral-800 pt-4">
      <h3 className="text-sm font-semibold">Export</h3>
      <label className="flex flex-col gap-1 text-xs text-neutral-400">
        Credit line on each card
        <input
          className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1.5 text-sm text-neutral-100"
          value={credit}
          onChange={(event) => setCredit(event.currentTarget.value)}
        />
        <span className="text-neutral-500">
          Provisional wording. Agree it with Freefly before posting.
        </span>
      </label>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className={button}
          disabled={working}
          onClick={() => void downloadCards()}
        >
          Download cards (PNG)
        </button>
        <button type="button" className={button} disabled={working} onClick={preview}>
          Preview cards
        </button>
        <button
          type="button"
          className={button}
          disabled={working}
          onClick={() => void downloadTags()}
        >
          Tags (CSV)
        </button>
        <button type="button" className={button} disabled={working} onClick={downloadStats}>
          Stats (CSV)
        </button>
      </div>
      {status && (
        <p
          role={status.kind === 'error' ? 'alert' : 'status'}
          className={`text-xs ${status.kind === 'error' ? 'text-red-400' : 'text-neutral-400'}`}
        >
          {status.text}
        </p>
      )}
      {previews && (
        <ul aria-label="Card previews" className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {previews.map((p) => (
            <li key={p.name}>
              <img src={p.url} alt={p.name} className="w-full rounded border border-neutral-800" />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
