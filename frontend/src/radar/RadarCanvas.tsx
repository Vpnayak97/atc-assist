import { useEffect, useRef } from 'react'

import { useStore } from '../state/store'
import type { Track } from '../state/types'
import { makeView } from './projection'
import { drawRangeRings } from './layers/rangeRings'
import { drawBearingLabels, drawSpokes } from './layers/bearingSpokes'
import { drawRunways } from './layers/runways'
import { drawAircraft } from './layers/aircraft'
import type { Hit } from './layers/aircraft'
import { drawPredictedPath } from './layers/predictedPath'
import { drawConflicts } from './layers/conflicts'
import { drawTrails } from './layers/trails'
import { drawMeasure } from './layers/measureTool'
import { positionNow } from './interpolation'
import { toScreen } from './projection'

export default function RadarCanvas() {
  const ref = useRef<HTMLCanvasElement>(null)
  const hits = useRef<Hit[]>([])

  useEffect(() => {
    const canvas = ref.current!
    const ctx = canvas.getContext('2d')!
    const parent = canvas.parentElement!
    let raf = 0

    const resize = () => {
      const dpr = window.devicePixelRatio || 1
      canvas.width = parent.clientWidth * dpr
      canvas.height = parent.clientHeight * dpr
      canvas.style.width = parent.clientWidth + 'px'
      canvas.style.height = parent.clientHeight + 'px'
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(parent)

    const frame = () => {
      const s = useStore.getState()
      const now = performance.now()
      const w = parent.clientWidth
      const h = parent.clientHeight
      const v = makeView(w, h, s.rangeNm)
      const byHex = new Map<string, Track>(s.tracks.map((t) => [t.hex, t]))
      const flags = new Map<string, string>()

      s.ops?.conflicts.forEach((c) => {
        flags.set(c.a, c.sev)
        flags.set(c.b, c.sev)
      })

      s.ops?.go_arounds.forEach((h) => flags.set(h, 'WARNING'))
      const seq = new Map((s.ops?.sequence?.entries ?? []).map((e) => [e.hex, e.pos] as [string, number]))
      const closed = new Set((s.ops?.runways ?? []).filter((r) => r.closed).map((r) => r.id))

      ctx.clearRect(0, 0, w, h)
      ctx.fillStyle = '#000'
      ctx.fillRect(0, 0, w, h)

      ctx.save()
      ctx.beginPath()
      ctx.arc(v.cx, v.cy, v.rangeNm * v.pxPerNm, 0, Math.PI * 2)
      ctx.clip()

      if (s.layers.spokes) drawSpokes(ctx, v)
      if (s.layers.rings) drawRangeRings(ctx, v)
      if (s.airport && s.layers.runways) drawRunways(ctx, v, s.airport, closed)
      if (s.layers.trails) drawTrails(ctx, v)

      if (s.ops) {
        drawConflicts(ctx, v, s.ops, byHex, s.recvAt, now, s.preview, s.layers.spacing)
      }

      hits.current = drawAircraft(
        ctx,
        v,
        s.tracks,
        s.recvAt,
        now,
        s.selected,
        s.layers,
        s.ptlMin,
        flags,
        seq
      )

      const sel = s.selected ? byHex.get(s.selected) : undefined

      if (sel && s.airport) {
        const [sx, sy] = toScreen(v, ...positionNow(sel, s.recvAt, now))
        ctx.strokeStyle = 'rgba(255,255,255,0.35)'
        ctx.setLineDash([3, 5])
        ctx.beginPath()
        ctx.arc(sx, sy, s.airport.sep_nm * v.pxPerNm, 0, Math.PI * 2)
        ctx.stroke()
        ctx.setLineDash([])
      }

      drawPredictedPath(ctx, v, sel, s.recvAt, now)
      drawMeasure(ctx, v, s.measure, byHex, s.recvAt, now)
      ctx.restore()

      ctx.strokeStyle = 'rgba(190,205,225,0.6)'
      ctx.beginPath()
      ctx.arc(v.cx, v.cy, v.rangeNm * v.pxPerNm, 0, Math.PI * 2)
      ctx.stroke()

      if (s.layers.spokes) drawBearingLabels(ctx, v)

      raf = requestAnimationFrame(frame)
    }

    raf = requestAnimationFrame(frame)

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
    }
  }, [])

  const onClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const r = ref.current!.getBoundingClientRect()
    const mx = e.clientX - r.left
    const my = e.clientY - r.top
    let best: Hit | null = null
    let bd = 16

    for (const h of hits.current) {
      const d = Math.hypot(h.sx - mx, h.sy - my)
      if (d < bd) {
        bd = d
        best = h
      }
    }

    const s = useStore.getState()

    if (s.tool === 'measure') {
      const v = makeView(r.width, r.height, s.rangeNm)
      const pt = best
        ? { x: 0, y: 0, hex: best.hex }
        : { x: (mx - v.cx) / v.pxPerNm, y: -(my - v.cy) / v.pxPerNm }
      const m = s.measure

      s.setMeasure(!m.a || (m.a && m.b) ? { a: pt, b: null } : { a: m.a, b: pt })
      return
    }

    s.select(best ? best.hex : null)
    if (best) s.setTab('flight')
  }

  return <canvas ref={ref} onClick={onClick} style={{ display: 'block', cursor: 'crosshair' }} />
}