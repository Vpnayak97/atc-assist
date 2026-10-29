import { useStore } from '../state/store'
import { recordTrails } from '../radar/layers/trails'

export function startSocket(): () => void {
  let ws: WebSocket | null = null
  let timer: number | undefined
  let closed = false
  const connect = () => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    ws = new WebSocket(`${proto}://${location.host}/ws`)
    ws.onopen = () => useStore.getState().setConnected(true)
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data)
      const st = useStore.getState()
      if (m.type === 'snapshot') { st.applySnapshot(m.airport, m.tracks, m.health); if (m.ops) st.applyOps(m.ops); recordTrails(m.tracks) }
      else if (m.type === 'tracks') { st.applyTracks(m.tracks); recordTrails(m.tracks) }
      else if (m.type === 'ops') st.applyOps(m.ops)
      else if (m.type === 'health') st.setHealth(m.health)
    }
    ws.onclose = () => {
      useStore.getState().setConnected(false)
      if (!closed) timer = window.setTimeout(connect, 2000)
    }
    ws.onerror = () => ws?.close()
  }
  connect()
  return () => { closed = true; window.clearTimeout(timer); ws?.close() }
}