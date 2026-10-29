import type { Track } from '../../state/types'
import { toScreen } from '../projection'
import type { View } from '../projection'

const trails = new Map<string, [number, number][]>()
const lastAt = new Map<string, number>()

export function recordTrails(tracks: Track[]) {
  const now = performance.now()
  const live = new Set<string>()
  for (const t of tracks) {
    live.add(t.hex)
    if (now - (lastAt.get(t.hex) ?? 0) < 6000) continue
    lastAt.set(t.hex, now)
    const a = trails.get(t.hex) ?? []
    a.push([t.x, t.y])
    if (a.length > 12) a.shift()
    trails.set(t.hex, a)
  }
  for (const k of [...trails.keys()]) if (!live.has(k)) { trails.delete(k); lastAt.delete(k) }
}

export function drawTrails(ctx: CanvasRenderingContext2D, v: View) {
  ctx.fillStyle = '#9fc4e6'
  for (const pts of trails.values()) {
    pts.forEach(([x, y], i) => {
      const [sx, sy] = toScreen(v, x, y)
      ctx.globalAlpha = 0.15 + 0.5 * (i / pts.length)
      ctx.fillRect(sx - 1, sy - 1, 2, 2)
    })
  }
  ctx.globalAlpha = 1
}