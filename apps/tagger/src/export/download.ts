import { CARD_HEIGHT, CARD_WIDTH, type Card } from './cards'
import { drawCard } from './draw'

// Browser I/O at the edge: canvases, blobs, and downloads. Nothing is uploaded.

export function renderCard(card: Card): HTMLCanvasElement {
  const canvas = document.createElement('canvas')
  canvas.width = CARD_WIDTH
  canvas.height = CARD_HEIGHT
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('This browser cannot draw the stat cards.')
  drawCard(ctx, card)
  return canvas
}

export function canvasToPng(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error('PNG export failed'))),
      'image/png',
    )
  })
}

export function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  // Give the browser a moment to start the download before freeing the URL.
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function downloadText(text: string, fileName: string, type: string) {
  downloadBlob(new Blob([text], { type }), fileName)
}
