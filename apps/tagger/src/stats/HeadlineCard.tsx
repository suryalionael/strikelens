import type { Corner, FightStats } from '../api/types'
import { CORNER_NAME } from './colors'
import { formatDuration, formatPercent, formatRate } from './format'
import { Swatch } from './Swatch'

const CORNERS: Corner[] = ['red', 'blue']

interface Props {
  stats: FightStats
  names: Record<Corner, string>
}

export function HeadlineCard({ stats, names }: Props) {
  const rows: { label: string; value: (c: Corner) => string }[] = [
    { label: 'Attempts', value: (c) => String(stats.fighters[c].totals.attempts) },
    { label: 'Landed', value: (c) => String(stats.fighters[c].totals.landed) },
    { label: 'Accuracy', value: (c) => formatPercent(stats.fighters[c].totals.accuracy) },
    {
      label: 'Strikes per minute',
      value: (c) => formatRate(stats.fighters[c].totals.strikes_per_minute),
    },
  ]

  return (
    <table aria-label="Headline stats" className="w-full text-sm">
      <caption className="mb-2 text-left text-xs text-neutral-500">
        Fight time {formatDuration(stats.fight_time_s)} over {stats.rounds.length} marked{' '}
        {stats.rounds.length === 1 ? 'round' : 'rounds'}
      </caption>
      <thead>
        <tr className="text-left text-xs text-neutral-400">
          <th className="font-normal" />
          {CORNERS.map((corner) => (
            <th key={corner} scope="col" className="py-1 font-normal">
              <span className="flex items-center gap-1.5">
                <Swatch corner={corner} />
                {CORNER_NAME[corner]}: {names[corner]}
              </span>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.label} className="border-t border-neutral-800">
            <th scope="row" className="py-1.5 text-left font-normal text-neutral-400">
              {row.label}
            </th>
            {CORNERS.map((corner) => (
              <td key={corner} className="py-1.5 text-lg font-semibold tabular-nums">
                {row.value(corner)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
