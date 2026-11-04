import type { Corner } from '../api/types'
import { CORNER_COLOR } from './colors'

export function Swatch({ corner }: { corner: Corner }) {
  return (
    <span
      aria-hidden
      className="inline-block size-2.5 rounded-sm"
      style={{ backgroundColor: CORNER_COLOR[corner] }}
    />
  )
}
