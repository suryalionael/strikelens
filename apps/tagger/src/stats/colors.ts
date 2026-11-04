import type { Corner } from '../api/types'

// Corner colours, checked with the dataviz palette validator against the panel
// (#171717) and page (#0a0a0a) surfaces: every check passes, protan CVD ΔE 19.2.
// Marks only. Text stays in neutral ink; the swatch beside it carries identity.
export const CORNER_COLOR: Record<Corner, string> = { red: '#e66767', blue: '#3987e5' }
export const CORNER_NAME: Record<Corner, string> = { red: 'Red', blue: 'Blue' }

export const GRID = '#262626'
export const AXIS_TEXT = '#a3a3a3'
export const SURFACE = '#0a0a0a'
