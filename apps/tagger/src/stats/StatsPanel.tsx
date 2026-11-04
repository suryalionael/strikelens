import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Corner, Fight, FightStats } from '../api/types'
import { ExportPanel } from '../export/ExportPanel'
import { CornerBarChart } from './CornerBarChart'
import { formatPercent, formatRate, mixRows, perRoundRows, targetRows } from './format'
import { HeadlineCard } from './HeadlineCard'

interface Props {
  fight: Fight | null
  /** Changes whenever a tag is saved, so the stats refresh. */
  refreshKey: number
}

const NO_NAMES: Record<Corner, string> = { red: '…', blue: '…' }

const percent = (n: number) => `${Math.round(n * 100)}%`

export function StatsPanel({ fight, refreshKey }: Props) {
  const [stats, setStats] = useState<FightStats | null>(null)
  const [names, setNames] = useState<Record<Corner, string>>(NO_NAMES)
  const [error, setError] = useState<string | null>(null)
  const [targetBasis, setTargetBasis] = useState<'landed' | 'attempted'>('landed')
  const fightId = fight?.id ?? null
  const redId = fight?.red_fighter_id ?? null
  const blueId = fight?.blue_fighter_id ?? null
  // Round marks change fight time, so a round save refreshes the stats too.
  const roundsKey = JSON.stringify(fight?.rounds ?? [])

  useEffect(() => {
    if (fightId === null) return
    let cancelled = false
    api
      .getStats(fightId)
      .then((loaded) => {
        if (cancelled) return
        setStats(loaded)
        setError(null)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
    return () => {
      cancelled = true
    }
  }, [fightId, refreshKey, roundsKey])

  useEffect(() => {
    if (redId === null || blueId === null) return
    let cancelled = false
    Promise.all([api.getFighter(redId), api.getFighter(blueId)])
      .then(([red, blue]) => {
        if (!cancelled) setNames({ red: red.name, blue: blue.name })
      })
      // Names are a nicety on the card; the stats still show without them.
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [redId, blueId])

  if (fightId === null) return null

  return (
    <section
      aria-label="Stats"
      className="flex flex-col gap-5 rounded border border-neutral-800 p-4"
    >
      <h2 className="font-semibold">Stats</h2>
      {error && (
        <p role="alert" className="text-xs text-red-400">
          Stats not updated: {error}
        </p>
      )}
      {!stats && !error && <p className="text-sm text-neutral-400">Loading stats…</p>}

      {stats && (
        <>
          <HeadlineCard stats={stats} names={names} />

          {stats.uncounted_tags > 0 && (
            <p role="status" className="text-xs text-amber-400">
              {stats.uncounted_tags} confirmed {stats.uncounted_tags === 1 ? 'tag is' : 'tags are'}{' '}
              outside every marked round and not counted.
            </p>
          )}
          {stats.rounds.some((r) => r.partial) && (
            <p className="text-xs text-neutral-400">
              A round marked partial ended early, so its counts are lower. Its strikes per minute
              uses the shorter round time.
            </p>
          )}

          {stats.rounds.length > 0 && (
            <CornerBarChart
              title="Attempts per round"
              rows={perRoundRows(stats)}
              value={(v) => v.attempts}
              formatValue={String}
              columns={[
                { header: 'Att', value: (v) => String(v.attempts) },
                { header: 'Land', value: (v) => String(v.landed) },
                { header: 'Acc', value: (v) => formatPercent(v.accuracy) },
                { header: 'SPM', value: (v) => formatRate(v.strikes_per_minute) },
              ]}
            />
          )}

          <CornerBarChart
            title="Weapon mix (attempts)"
            rows={mixRows(stats, 'weapon_groups')}
            value={(v) => v.attempts}
            formatValue={String}
            columns={[
              { header: 'Att', value: (v) => String(v.attempts) },
              { header: 'Land', value: (v) => String(v.landed) },
              { header: 'Share', value: (v) => formatPercent(v.share) },
            ]}
          />

          <CornerBarChart
            title={`Target distribution (${targetBasis === 'landed' ? 'landed strikes' : 'all attempts'})`}
            rows={targetRows(stats, targetBasis)}
            value={(v) => v.share}
            formatValue={percent}
            domainMax={1}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            columns={[
              { header: 'Count', value: (v) => String(v.count) },
              { header: 'Share', value: (v) => formatPercent(v.share) },
            ]}
            controls={
              <div role="group" aria-label="Target basis" className="flex gap-1 text-xs">
                {(['landed', 'attempted'] as const).map((basis) => (
                  <button
                    key={basis}
                    type="button"
                    aria-pressed={targetBasis === basis}
                    onClick={() => setTargetBasis(basis)}
                    className="rounded border border-neutral-700 px-2 py-0.5 text-neutral-300 hover:bg-neutral-800 aria-pressed:bg-neutral-100 aria-pressed:text-neutral-950"
                  >
                    {basis === 'landed' ? 'Landed' : 'All attempts'}
                  </button>
                ))}
              </div>
            }
          />

          <aside
            aria-label="Provisional definitions"
            className="rounded border border-amber-900/60 bg-amber-950/30 p-3 text-xs text-amber-200"
          >
            <p className="font-semibold">Provisional definitions</p>
            <p className="mt-1 text-amber-200/80">
              These numbers follow rules not yet confirmed with Freefly:
            </p>
            <ul className="mt-1 list-inside list-disc">
              {stats.provisional_rules.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
          </aside>
          {fight && <ExportPanel fight={fight} stats={stats} names={names} />}
        </>
      )}
    </section>
  )
}
