import type { View } from '../projection'

export function drawRangeRings(ctx: CanvasRenderingContext2D, v: View) {
  const step = v.rangeNm <= 20 ? 5 : v.rangeNm <= 40 ? 10 : 20
  ctx.strokeStyle = 'rgba(190,205,225,0.35)'
  ctx.fillStyle = 'rgba(190,205,225,0.75)'
  ctx.lineWidth = 1
  ctx.font = '11px ui-monospace, Consolas, monospace'
  for (let r = step; r <= v.rangeNm + 0.01; r += step) {
    ctx.beginPath()
    ctx.arc(v.cx, v.cy, r * v.pxPerNm, 0, Math.PI * 2)
    ctx.stroke()
    ctx.fillText(`${r}`, v.cx + 4, v.cy - r * v.pxPerNm - 3)
  }
}