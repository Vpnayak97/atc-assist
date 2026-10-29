import type { Track } from '../../state/types'
import type { Layers } from '../../state/store'
import { positionNow } from '../interpolation'
import { toScreen } from '../projection'
import type { View } from '../projection'
import { SEV_COLOR } from './conflicts'

export interface Hit { hex: string; sx: number; sy: number }

const altText = (t: Track) =>
  t.gnd ? 'GND' : t.alt == null ? '---' : t.alt >= 18000 ? `FL${Math.round(t.alt / 100)}` : `${Math.round(t.alt)}FT`
const trend = (t: Track) => (t.vr == null ? '' : t.vr > 300 ? '↑' : t.vr < -300 ? '↓' : '')

function color(t: Track, selected: boolean, sev?: string): string {
  if (selected) return '#ffffff'
  if (sev) return SEV_COLOR[sev as keyof typeof SEV_COLOR]
  if (t.emg) return '#ff3b3b'
  if (t.pri < 3) return '#ffd400'
  return t.gnd ? '#7fa8c9' : '#ff9f1a'
}

export function drawAircraft(
  ctx: CanvasRenderingContext2D,
  v: View,
  tracks: Track[],
  recvAt: number,
  now: number,
  selected: string | null,
  layers: Layers,
  ptlMin: number,
  flags: Map<string, string>,
  seq: Map<string, number>
): Hit[] {
  const hits: Hit[] = []
  ctx.font = '11px ui-monospace, Consolas, monospace'

  for (const t of tracks) {
    const [x, y] = positionNow(t, recvAt, now)
    const [sx, sy] = toScreen(v, x, y)

    if (Math.hypot(sx - v.cx, sy - v.cy) > v.rangeNm * v.pxPerNm + 20) continue

    const sev = flags.get(t.hex)
    const c = color(t, t.hex === selected, sev)

    ctx.globalAlpha = t.stale ? 0.45 : 1
    ctx.strokeStyle = c
    ctx.fillStyle = c
    ctx.lineWidth = 1.5

    if (layers.vectors && t.gs != null && t.trk != null && !t.gnd) {
      const len = (t.gs * ptlMin * 60) / 3600 * v.pxPerNm
      const a = (t.trk * Math.PI) / 180

      ctx.beginPath()
      ctx.moveTo(sx, sy)
      ctx.lineTo(sx + len * Math.sin(a), sy - len * Math.cos(a))
      ctx.stroke()
    }

    ctx.save()
    ctx.translate(sx, sy)

    if (t.gnd) {
      ctx.strokeRect(-3, -3, 6, 6)
    } else {
      ctx.rotate(((t.trk ?? 0) * Math.PI) / 180)
      ctx.beginPath()
      ctx.moveTo(0, -7)
      ctx.lineTo(5, 5)
      ctx.lineTo(-5, 5)
      ctx.closePath()
      ctx.stroke()
    }

    ctx.restore()

    if (sev || t.emg) {
      ctx.beginPath()
      ctx.arc(sx, sy, 11, 0, Math.PI * 2)
      ctx.stroke()
    }

    const sim = t.src === 'synthetic' ? ' [SIM]' : ''
    const n = seq.get(t.hex)
    const tag = (n ? ` #${n}` : '') + (t.phase === 'GO_AROUND' ? ' GA' : t.phase === 'HOLDING' ? ' HOLD' : '')
    ctx.fillText(`${t.callsign ?? t.hex.toUpperCase()}${t.emg ? ' EMG' : ''}${tag}${sim}`, sx + 12, sy - 10)

    if (layers.labels) {
      ctx.fillText(
        `${altText(t)}${trend(t)}${t.sel != null && !t.gnd && Math.abs(t.sel - (t.alt ?? 0)) > 200 ? '>' + Math.round(t.sel / 100) : ''}`,
        sx + 12,
        sy + 2
      )
      ctx.fillText(`${t.gs ?? '--'}KT ${t.type ?? ''}/${t.wake}`, sx + 12, sy + 14)

      const eta = t.pred?.eta
      if (eta) {
        ctx.fillText(`ETA ${Math.floor(eta.s / 60)}:${String(eta.s % 60).padStart(2, '0')}`, sx + 12, sy + 26)
      }
    }

    ctx.globalAlpha = 1
    hits.push({ hex: t.hex, sx, sy })
  }

  return hits
}
