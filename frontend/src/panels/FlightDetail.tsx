import { useEffect, useState } from 'react'
import { getJSON, postJSON } from '../api/client'
import { useStore } from '../state/store'

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

export default function FlightDetail() {
  const t = useStore((s) => s.tracks.find((x) => x.hex === s.selected))
  const hex = t?.hex
  const [why, setWhy] = useState<{ eta: any[]; anom: any[] }>({ eta: [], anom: [] })
  useEffect(() => {
    if (!hex) return
    const load = () => getJSON<any>(`/api/flights/${hex}`).then((d) =>
      setWhy({ eta: d.predictions?.eta?.explanation ?? [], anom: d.predictions?.anomaly?.explanation ?? [] })).catch(() => {})
    load(); const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [hex])
  if (!t) return <div className="detail dim">Click an aircraft on the radar or in a list.</div>
  const e = t.pred?.eta
  const rows: [string, string][] = [
    ['Callsign', t.callsign ?? '-'], ['Hex', t.hex.toUpperCase()], ['Type / wake', `${t.type ?? '-'} / ${t.wake}`],
    ['Phase', `${t.phase}${t.rwy ? ' RWY ' + t.rwy : ''}`], ['Altitude', t.gnd ? 'ground' : `${t.alt ?? '-'} ft`],
    ['Selected alt', t.sel != null ? `${t.sel} ft` : '-'], ['Ground speed', `${t.gs ?? '-'} kt`],
    ['Track / V/S', `${t.trk ?? '-'}° / ${t.vr ?? '-'} fpm`], ['Squawk', t.sq ?? '-'],
    ['Distance', `${t.dist} nm @ ${t.brg}°`], ['Data', `${t.age} s old (${t.src}), quality ${t.q.toFixed(2)}`],
  ]
  return (
    <div className="detail">
      <h3>{t.callsign ?? t.hex.toUpperCase()}</h3>
      <table><tbody>{rows.map(([k, v]) => <tr key={k}><td className="dim">{k}</td><td>{v}</td></tr>)}</tbody></table>
      <div style={{ marginTop: 6 }}>
        {t.emg
          ? <button onClick={() => postJSON(`/api/flights/${t.hex}/emergency`, { declare: false }).catch(() => {})}>CLEAR EMERGENCY</button>
          : <button onClick={() => postJSON(`/api/flights/${t.hex}/emergency`, { declare: true }).catch(() => {})}>DECLARE EMERGENCY</button>}
        {[['MEDICAL', 1], ['STATE', 2], ['NORMAL', 3]].map(([l, p]) => (
          <button key={l as string} onClick={() => postJSON(`/api/flights/${t.hex}/priority`, { priority: p }).catch(() => {})}>{l}</button>
        ))}
      </div>
      {e && (<>
        <h3>LANDING ETA</h3>
        <div>{mmss(e.s)}{e.lo != null && e.hi != null ? ` (${mmss(e.lo)} – ${mmss(e.hi)})` : ''} <span className="dim">[{e.src}]</span></div>
        {e.phys != null && <div className="small dim">physics only: {mmss(e.phys)}</div>}
        {why.eta.map((w) => <div key={w.feature} className="small">{w.feature}: {w.contrib > 0 ? '+' : ''}{w.contrib} s</div>)}
      </>)}
      {t.pred?.anom?.flag && (<>
        <h3 style={{ color: 'var(--warn)' }}>UNUSUAL APPROACH</h3>
        {why.anom.map((w) => <div key={w.feature} className="small">{w.feature}: {w.value} (typical {w.typical})</div>)}
      </>)}
    </div>
  )
}