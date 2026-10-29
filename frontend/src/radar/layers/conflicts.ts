import type { Ops, Track } from '../../state/types'
import { positionNow } from '../interpolation'
import { toScreen } from '../projection'
import type { View } from '../projection'

export const SEV_COLOR = { WARNING: '#ff3b3b', CAUTION: '#ffb020', ADVISORY: '#ffe14d' } as const
const SPC_COLOR = { ok: '#3ddc84', marginal: '#ffb020', short: '#ff3b3b' } as const

export function drawConflicts(ctx: CanvasRenderingContext2D, v: View, ops: Ops, byHex: Map<string, Track>,
                              recvAt: number, now: number, preview: string | null, showSpacing: boolean) {
  ctx.font = '11px ui-monospace, Consolas, monospace'
  ctx.lineWidth = 1.5
  if (showSpacing) {
    for (const s of ops.spacing) {
      const L = byHex.get(s.lead), F = byHex.get(s.follow)
      if (!L || !F) continue
      const [lx, ly] = toScreen(v, ...positionNow(L, recvAt, now))
      const [fx, fy] = toScreen(v, ...positionNow(F, recvAt, now))
      ctx.strokeStyle = ctx.fillStyle = SPC_COLOR[s.status]
      ctx.globalAlpha = 0.8
      ctx.beginPath(); ctx.moveTo(lx, ly); ctx.lineTo(fx, fy); ctx.stroke()
      ctx.fillText(`${s.dist.toFixed(1)}/${s.req} nm ${s.lw}>${s.fw}`, (lx + fx) / 2 + 6, (ly + fy) / 2)
    }
  }
  for (const c of ops.conflicts) {
    const A = byHex.get(c.a), B = byHex.get(c.b)
    if (!A || !B) continue
    const col = SEV_COLOR[c.sev]
    ctx.globalAlpha = c.sev === 'WARNING' ? 0.65 + 0.35 * Math.sin(now / 150) : 1
    ctx.strokeStyle = ctx.fillStyle = col
    const [ax, ay] = toScreen(v, ...positionNow(A, recvAt, now))
    const [bx, by] = toScreen(v, ...positionNow(B, recvAt, now))
    ctx.setLineDash([4, 4])
    for (const [sx, sy] of [[ax, ay], [bx, by]]) { ctx.beginPath(); ctx.arc(sx, sy, c.hreq * v.pxPerNm, 0, Math.PI * 2); ctx.stroke() }
    const [pax, pay] = toScreen(v, c.ax, c.ay)
    const [pbx, pby] = toScreen(v, c.bx, c.by)
    ctx.beginPath(); ctx.moveTo(pax, pay); ctx.lineTo(pbx, pby); ctx.stroke()
    for (const [sx, sy] of [[pax, pay], [pbx, pby]]) { ctx.beginPath(); ctx.moveTo(sx - 4, sy - 4); ctx.lineTo(sx + 4, sy + 4); ctx.moveTo(sx + 4, sy - 4); ctx.lineTo(sx - 4, sy + 4); ctx.stroke() }
    ctx.setLineDash([])
    ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke()
    ctx.fillText(`${c.los ? 'LOS' : 'T-' + Math.round(c.t_viol) + 's'}  ${c.h_min.toFixed(1)}nm/${Math.round(c.v_min)}ft`, (ax + bx) / 2 + 8, (ay + by) / 2 - 8)
  }
  ctx.globalAlpha = 1
  for (const adv of ops.advisories) {
    if (adv.id !== preview || adv.path.length < 2) continue
    ctx.strokeStyle = ctx.fillStyle = '#7fe0ff'
    ctx.setLineDash([6, 4]); ctx.lineWidth = 2
    ctx.beginPath()
    adv.path.forEach(([x, y], i) => { const [sx, sy] = toScreen(v, x, y); if (i === 0) ctx.moveTo(sx, sy); else ctx.lineTo(sx, sy) })
    ctx.stroke(); ctx.setLineDash([]); ctx.lineWidth = 1.5
    const [ex, ey] = toScreen(v, ...adv.path[adv.path.length - 1])
    ctx.fillText(adv.short, ex + 8, ey)
  }
}