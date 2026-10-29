import type { Track } from '../../state/types'
import { positionNow } from '../interpolation'
import { toScreen } from '../projection'
import type { View } from '../projection'

// Selected aircraft: predicted position and altitude at +30 s and +60 s (dead reckoning + altitude model).
export function drawPredictedPath(ctx: CanvasRenderingContext2D, v: View, t: Track | undefined, recvAt: number, now: number) {
  if (!t || t.gnd || t.gs == null || t.trk == null) return
  const [x, y] = positionNow(t, recvAt, now)
  const a = (t.trk * Math.PI) / 180
  ctx.font = '10px ui-monospace, Consolas, monospace'
  for (const h of [30, 60]) {
    const d = (t.gs * h) / 3600
    const [sx, sy] = toScreen(v, x + d * Math.sin(a), y + d * Math.cos(a))
    ctx.strokeStyle = '#7fe0ff'; ctx.fillStyle = '#7fe0ff'
    ctx.beginPath(); ctx.arc(sx, sy, 3, 0, Math.PI * 2); ctx.stroke()
    const p = t.pred?.alt_pred?.find((q) => q.h === h)
    ctx.fillText(`+${h}s${p ? ' ' + p.alt + 'ft' : ''}${p?.src === 'ml' ? ' ·ML' : ''}`, sx + 6, sy + 3)
  }
}