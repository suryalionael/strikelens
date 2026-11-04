import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ReactNode } from 'react'
import type { Corner } from '../api/types'
import { AXIS_TEXT, CORNER_COLOR, CORNER_NAME, GRID, SURFACE } from './colors'
import type { CornerRow } from './format'
import { DASH } from './format'
import { Swatch } from './Swatch'

const CORNERS: Corner[] = ['red', 'blue']

interface Column<V> {
  header: string
  value: (v: V) => string
}

interface Props<V> {
  title: string
  rows: CornerRow<V>[]
  /** The number each bar shows. Null leaves a gap, never a zero bar. */
  value: (v: V) => number | null
  formatValue: (n: number) => string
  /** Columns for the table view under the chart. */
  columns: Column<V>[]
  domainMax?: number
  /** Fixed y ticks, for values that are not whole numbers (shares). */
  ticks?: number[]
  /** Shown next to the title, for example a toggle. */
  controls?: ReactNode
}

/** Grouped bars, red and blue per category, with a table view of the same rows. */
export function CornerBarChart<V>({
  title,
  rows,
  value,
  formatValue,
  columns,
  domainMax,
  ticks,
  controls,
}: Props<V>) {
  const data = rows.map((row) => ({
    label: row.label,
    red: value(row.red),
    blue: value(row.blue),
  }))

  return (
    <figure className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <figcaption className="text-sm font-semibold">{title}</figcaption>
        {controls}
      </div>
      <div className="h-48 w-full" aria-hidden>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barGap={2} margin={{ top: 4, right: 4, bottom: 0, left: -16 }}>
            <CartesianGrid vertical={false} stroke={GRID} />
            <XAxis
              dataKey="label"
              tick={{ fill: AXIS_TEXT, fontSize: 11 }}
              axisLine={{ stroke: GRID }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: AXIS_TEXT, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              allowDecimals={ticks !== undefined}
              ticks={ticks}
              tickFormatter={formatValue}
              domain={[0, domainMax ?? 'auto']}
            />
            <Tooltip
              // Red first, like the bars and the legend.
              itemSorter={(item) => (item.dataKey === 'red' ? 0 : 1)}
              cursor={{ fill: GRID, opacity: 0.4 }}
              contentStyle={{ background: '#171717', border: `1px solid ${GRID}`, fontSize: 12 }}
              labelStyle={{ color: '#e5e5e5' }}
              itemStyle={{ color: '#e5e5e5' }}
              formatter={(v, name) => [typeof v === 'number' ? formatValue(v) : DASH, name]}
            />
            <Legend
              // Keep the bar order (red, then blue) instead of sorting by name.
              itemSorter={null}
              wrapperStyle={{ fontSize: 12, color: AXIS_TEXT }}
              formatter={(name: string) => <span style={{ color: AXIS_TEXT }}>{name}</span>}
            />
            {CORNERS.map((corner) => (
              <Bar
                key={corner}
                dataKey={corner}
                name={CORNER_NAME[corner]}
                fill={CORNER_COLOR[corner]}
                stroke={SURFACE}
                strokeWidth={0}
                maxBarSize={24}
                radius={[4, 4, 0, 0]}
                isAnimationActive={false}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <details className="text-xs text-neutral-400">
        <summary className="cursor-pointer select-none">Table view</summary>
        <table aria-label={`${title} table`} className="mt-1 w-full">
          <thead>
            <tr className="text-left">
              <th className="font-normal" />
              {CORNERS.map((corner) => (
                <th key={corner} colSpan={columns.length} scope="colgroup" className="font-normal">
                  <span className="flex items-center gap-1.5">
                    <Swatch corner={corner} />
                    {CORNER_NAME[corner]}
                  </span>
                </th>
              ))}
            </tr>
            <tr className="text-left text-neutral-500">
              <th className="font-normal" />
              {CORNERS.flatMap((corner) =>
                columns.map((col) => (
                  <th key={`${corner}-${col.header}`} scope="col" className="font-normal">
                    {col.header}
                  </th>
                )),
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-t border-neutral-800">
                <th scope="row" className="py-0.5 text-left font-normal capitalize">
                  {row.label}
                </th>
                {CORNERS.flatMap((corner) =>
                  columns.map((col) => (
                    <td key={`${corner}-${col.header}`} className="tabular-nums">
                      {col.value(row[corner])}
                    </td>
                  )),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  )
}
