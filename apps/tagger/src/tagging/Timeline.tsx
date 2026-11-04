import { memo, type MouseEvent } from 'react'
import type { Corner, Tag } from '../api/types'
import type { RoundDraft } from '../fight/rounds'
import { usePlayer } from '../player/PlayerContext'
import { CORNER_COLOR, CORNER_NAME } from '../stats/colors'
import {
  markers as buildMarkers,
  position,
  roundBands,
  timeAt,
  timelineRange,
  type Marker,
  type MarkerShape,
} from './timelineLayout'

const CORNERS: Corner[] = ['red', 'blue']
const LANE = 'relative h-6'

interface Props {
  tags: readonly Tag[]
  rounds: readonly RoundDraft[]
  selectedId?: string | null
  /** Must be stable (for example a state setter), or markers redraw every frame. */
  onSelect?: (id: string) => void
}

function shapeStyle(shape: MarkerShape, color: string) {
  if (shape === 'ring') return { border: `2px solid ${color}`, background: 'transparent' }
  return { background: color }
}

const MarkerDot = ({
  marker,
  selected,
  onSeek,
  onSelect,
}: {
  marker: Marker
  selected: boolean
  onSeek: (seconds: number) => void
  onSelect?: (id: string) => void
}) => (
  <button
    type="button"
    // Hundreds of markers would flood the Tab order; the tag list and player keys
    // cover keyboard use. Screen readers still get the label.
    tabIndex={-1}
    aria-label={marker.label}
    title={marker.label}
    aria-pressed={selected}
    onClick={(event) => {
      event.stopPropagation()
      onSeek(marker.timestamp_ms / 1000)
      onSelect?.(marker.id)
    }}
    className={`absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 hover:scale-150 ${
      marker.shape === 'square' ? 'rounded-[1px]' : 'rounded-full'
    } ${selected ? 'z-10 scale-150 outline-2 outline-offset-1 outline-neutral-100' : ''}`}
    style={{ left: `${marker.left}%`, ...shapeStyle(marker.shape, CORNER_COLOR[marker.fighter]) }}
  />
)

/**
 * One lane's markers. Memoised on plain values, so the playhead can move every
 * frame without rebuilding or redrawing the markers.
 */
const MarkerLayer = memo(function MarkerLayer({
  tags,
  corner,
  start_ms,
  end_ms,
  selectedId,
  onSeek,
  onSelect,
}: {
  tags: readonly Tag[]
  corner: Corner
  start_ms: number
  end_ms: number
  selectedId: string | null
  onSeek: (seconds: number) => void
  onSelect?: (id: string) => void
}) {
  const lane = buildMarkers(
    tags.filter((t) => t.fighter === corner),
    { start_ms, end_ms },
  )
  return (
    <>
      {lane.map((marker) => (
        <MarkerDot
          key={marker.id}
          marker={marker}
          selected={marker.id === selectedId}
          onSeek={onSeek}
          onSelect={onSelect}
        />
      ))}
    </>
  )
})

export function Timeline({ tags, rounds, selectedId = null, onSelect }: Props) {
  const { currentTime, duration, seek } = usePlayer()
  const now_ms = Math.round(currentTime * 1000)
  const lastTag_ms = tags.reduce((max, t) => Math.max(max, t.timestamp_ms), 0)
  // Only an open round grows with the playhead; otherwise the range stays put.
  const hasOpenRound = rounds.some((r) => r.end_ms === null)
  const latest_ms = hasOpenRound ? Math.max(now_ms, lastTag_ms) : lastTag_ms
  const range = timelineRange(rounds, Math.round(duration * 1000), latest_ms)
  const bands = roundBands(rounds, range, latest_ms)

  const onTrackClick = (event: MouseEvent<HTMLDivElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    if (box.width === 0) return
    seek(timeAt(((event.clientX - box.left) / box.width) * 100, range) / 1000)
  }

  return (
    <div aria-label="Tag timeline" role="group" className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs text-neutral-500">
        <span>Timeline · click a marker or the track to jump there</span>
        <span className="flex items-center gap-3" aria-label="Marker shapes">
          {(
            [
              ['filled', 'landed'],
              ['ring', 'missed'],
              ['square', 'blocked'],
            ] as const
          ).map(([shape, outcome]) => (
            <span key={outcome} className="flex items-center gap-1">
              <span
                aria-hidden
                className={`inline-block size-2.5 ${shape === 'square' ? 'rounded-[1px]' : 'rounded-full'}`}
                style={shapeStyle(shape, '#a3a3a3')}
              />
              {outcome}
            </span>
          ))}
        </span>
      </div>

      <div className="flex gap-2">
        <div className="flex w-10 flex-col text-xs text-neutral-400">
          <span className="h-4" />
          {CORNERS.map((corner) => (
            <span key={corner} className="flex h-6 items-center">
              {CORNER_NAME[corner]}
            </span>
          ))}
        </div>

        <div
          data-testid="timeline-track"
          className="relative flex-1 cursor-pointer rounded bg-neutral-900"
          onClick={onTrackClick}
        >
          <div className="relative h-4">
            {bands.map((band) => (
              <span
                key={band.number}
                className="absolute top-0 text-[10px] text-neutral-400"
                style={{ left: `${band.left}%` }}
              >
                R{band.number}
                {band.open ? ' (open)' : ''}
              </span>
            ))}
          </div>
          {bands.map((band) => (
            <div
              key={band.number}
              aria-hidden
              data-testid={`round-band-${band.number}`}
              className={`absolute top-4 bottom-0 bg-neutral-800/60 ${
                band.open ? 'border-r border-dashed border-neutral-500' : ''
              }`}
              style={{ left: `${band.left}%`, width: `${band.width}%` }}
            />
          ))}
          {CORNERS.map((corner) => (
            <div key={corner} className={LANE} aria-label={`${CORNER_NAME[corner]} lane`}>
              <MarkerLayer
                tags={tags}
                corner={corner}
                start_ms={range.start_ms}
                end_ms={range.end_ms}
                selectedId={selectedId}
                onSeek={seek}
                onSelect={onSelect}
              />
            </div>
          ))}
          <div
            aria-hidden
            data-testid="playhead"
            className="pointer-events-none absolute top-0 bottom-0 w-px bg-neutral-100"
            style={{ left: `${position(now_ms, range)}%` }}
          />
        </div>
      </div>
    </div>
  )
}
