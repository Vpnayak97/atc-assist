import type { Pt, Track } from '../../state/types'
import { positionNow } from '../interpolation'
import { toScreen } from '../projection'
import type { View } from '../projection'

export function resolvePt(p: Pt, byHex: Map<string, Track>, recvAt: number, now: number): [number, number] {
  const t = p.hex ? byHex.get(p.hex) : undefined
  return t ? positionNow(t, recvAt, now) : [p.x, p.y]
}

export function drawMeasure(ctx: CanvasRenderingContext2D, v: View, m: { a: Pt | null; b: Pt | null },
                            byHex: Map<string, Track>, recvAt: number, now: number) {
  if (!m.a) return
  const [ax, ay] = resolvePt(m.a, byHex, recvAt, now)
  const [sax, say] = toScreen(v, ax, ay)
  ctx.strokeStyle = '#7fe0ff'; ctx.fillStyle = '#7fe0ff'; ctx.lineWidth = 1
  ctx.beginPath(); ctx.arc(sax, say, 4, 0, Math.PI * 2); ctx.stroke()
  if (!m.b) return
  const [bx, by] = resolvePt(m.b, byHex, recvAt, now)
  const [sbx, sby] = toScreen(v, bx, by)
  ctx.beginPath(); ctx.moveTo(sax, say); ctx.lineTo(sbx, sby); ctx.stroke()
  const dx = bx - ax, dy = by - ay
  const dist = Math.hypot(dx, dy)
  const brg = ((Math.atan2(dx, dy) * 180) / Math.PI + 360) % 360
  const gs = m.a.hex ? byHex.get(m.a.hex)?.gs : null
  const eta = gs ? ` · ${((dist / gs) * 60).toFixed(1)} min @ ${gs} kt` : ''
  ctx.font = '11px ui-monospace, Consolas, monospace'
  ctx.fillText(`${dist.toFixed(1)} nm  ${String(Math.round(brg)).padStart(3, '0')}°${eta}`, (sax + sbx) / 2 + 6, (say + sby) / 2 - 6)
}