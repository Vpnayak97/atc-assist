import type { Track } from '../state/types'

// Between 1 Hz pushes, advance along the track at ground speed (same model as the backend).
export function positionNow(t: Track, recvAt: number, now: number): [number, number] {
  const dt = Math.min(Math.max((now - recvAt) / 1000, 0), 3)
  if (t.gs == null || t.trk == null || dt === 0) return [t.x, t.y]
  const d = (t.gs * dt) / 3600
  const a = (t.trk * Math.PI) / 180
  return [t.x + d * Math.sin(a), t.y + d * Math.cos(a)]
}