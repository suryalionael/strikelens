import type { Player } from '../player/usePlayerState'

/** A Player with no video behind it, for components that only read player state. */
export function fakePlayer(overrides: Partial<Player> = {}): Player {
  return {
    src: 'blob:fight',
    fileName: 'fight.mp4',
    currentTime: 0,
    duration: 600,
    playing: false,
    rate: 1,
    fps: 30,
    loadFile: vi.fn(),
    togglePlay: vi.fn(),
    pause: vi.fn(),
    seek: vi.fn(),
    stepFrame: vi.fn(),
    setRate: vi.fn(),
    setFps: vi.fn(),
    videoRef: { current: null },
    videoHandlers: {},
    ...overrides,
  }
}
