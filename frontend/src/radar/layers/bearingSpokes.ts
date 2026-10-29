import type { View } from '../projection'

export function drawSpokes(ctx: CanvasRenderingContext2D, v: View) {
  const R = v.rangeNm * v.pxPerNm
  ctx.strokeStyle = 'rgba(190,205,225,0.3)'
  ctx.lineWidth = 1
  for (let b = 0; b < 360; b += 30) {
    const a = (b * Math.PI) / 180
    ctx.beginPath()
    ctx.moveTo(v.cx, v.cy)
    ctx.lineTo(v.cx + R * Math.sin(a), v.cy - R * Math.cos(a))
    ctx.stroke()
  }
}

export function drawBearingLabels(ctx: CanvasRenderingContext2D, v: View) {
  const R = v.rangeNm * v.pxPerNm + 14
  ctx.fillStyle = 'rgba(190,205,225,0.8)'
  ctx.font = '11px ui-monospace, Consolas, monospace'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  for (let b = 0; b < 360; b += 30) {
    const a = (b * Math.PI) / 180
    ctx.fillText(String(b).padStart(3, '0'), v.cx + R * Math.sin(a), v.cy - R * Math.cos(a))
  }
  ctx.textAlign = 'start'
  ctx.textBaseline = 'alphabetic'
}