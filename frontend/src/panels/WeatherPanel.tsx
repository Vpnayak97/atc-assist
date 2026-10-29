import { useEffect, useState } from 'react'
import { getJSON } from '../api/client'

interface Wx {
  ok: boolean; error: string | null; best: string | null; observed: Record<string, number>
  metar: { raw: string; wdir: number | null; wspd: number | null; wgst: number | null; vrb: boolean; qnh: number | null; vis: string | null; temp: string | null } | null
  runways: { ident: string; head: number; cross: number }[]
}

export default function WeatherPanel() {
  const [wx, setWx] = useState<Wx | null>(null)
  useEffect(() => {
    const load = () => getJSON<Wx>('/api/weather').then(setWx).catch(() => {})
    load(); const id = setInterval(load, 30000)
    return () => clearInterval(id)
  }, [])
  if (!wx) return <div className="detail dim">Loading weather…</div>
  if (!wx.metar) return <div className="detail dim">No METAR yet{wx.error ? `: ${wx.error}` : ''}</div>
  const m = wx.metar
  return (
    <div className="detail">
      <h3>METAR</h3>
      <div className="small">{m.raw}</div>
      <div>Wind {m.vrb ? 'VRB' : String(m.wdir).padStart(3, '0') + '°'} {m.wspd ?? '-'} kt{m.wgst ? ` G${m.wgst}` : ''} · QNH {m.qnh ?? '-'} · Vis {m.vis ?? '-'} · {m.temp ?? '-'}°C</div>
      <h3>RUNWAY WIND COMPONENTS</h3>
      <table><thead><tr><th>RWY</th><th>HEAD</th><th>CROSS</th><th>ARR/30MIN</th></tr></thead>
        <tbody>{wx.runways.map((r) => (
          <tr key={r.ident} className={r.ident === wx.best ? 'sel' : ''}>
            <td>{r.ident}{r.ident === wx.best ? ' ★' : ''}</td>
            <td>{r.head >= 0 ? `+${r.head}` : `${r.head} TAIL`}</td><td>{r.cross}</td><td>{wx.observed[r.ident] ?? 0}</td>
          </tr>))}</tbody></table>
      <div className="small dim">★ best headwind. Runway headings are true; METAR wind is magnetic (set ATC_MAGNETIC_VARIATION_DEG).</div>
    </div>
  )
}