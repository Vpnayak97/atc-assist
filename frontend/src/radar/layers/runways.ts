import type { Airport } from '../../state/types'
import { toScreen } from '../projection'
import type { View } from '../projection'

export function drawRunways(ctx: CanvasRenderingContext2D, v: View, ap: Airport) {
  ctx.font = '10px ui-monospace, Consolas, monospace'
  for (const rw of ap.runways) {
    const [a, b] = rw.ends
    if (!a || !b) continue
    const [ax, ay] = toScreen(v, a.x, a.y)
    const [bx, by] = toScreen(v, b.x, b.y)
    ctx.strokeStyle = '#cfe3ff'
    ctx.lineWidth = Math.max(2, 0.1 * v.pxPerNm)
    ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke()

    // extended centrelines, 10 nm on the approach side of each end
    ctx.strokeStyle = 'rgba(140,200,255,0.45)'
    ctx.lineWidth = 1
    ctx.setLineDash([6, 6])
    for (const e of rw.ends) {
      const h = (e.hdg * Math.PI) / 180
      const [ex, ey] = toScreen(v, e.x - 10 * Math.sin(h), e.y - 10 * Math.cos(h))
      const [sx, sy] = toScreen(v, e.x, e.y)
      ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(ex, ey); ctx.stroke()
    }
    ctx.setLineDash([])
    ctx.fillStyle = '#9fd0ff'
    ctx.fillText(a.ident, ax + 4, ay - 4)
    ctx.fillText(b.ident, bx + 4, by - 4)
  }
}