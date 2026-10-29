import { useStore } from '../state/store'

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

export default function StripsPanel() {
  const { tracks, ops, selected, select } = useStore()
  const spacing = new Map((ops?.spacing ?? []).map((s) => [s.follow, s]))
  const arr = tracks.filter((t) => t.pred?.eta && !t.gnd).sort((a, b) => a.pred!.eta!.s - b.pred!.eta!.s)
  const dep = tracks.filter((t) => ['TAXI', 'LINEUP', 'TAKEOFF_ROLL'].includes(t.phase) || (t.phase === 'CLIMB' && t.dist < 15 && (t.alt ?? 0) < 6000))
  const strip = (t: (typeof tracks)[number], i: number, eta: boolean) => {
    const sp = spacing.get(t.hex)
    return (
      <div key={t.hex} className={`strip${t.hex === selected ? ' sel' : ''}${t.emg ? ' emg' : ''}`} onClick={() => select(t.hex)}>
        <b>{eta ? i + 1 : '·'}</b> <b>{t.callsign ?? t.hex.toUpperCase()}</b> <span className={`wake wake-${t.wake}`}>{t.wake}</span> {t.type ?? '-'}
        <span className="dim"> RWY {t.rwy ?? '--'}</span>
        {eta && <span> ETA {mmss(t.pred!.eta!.s)}</span>}
        <span className="dim"> {t.gnd ? 'GND' : t.alt} ft · {t.gs ?? '-'} kt</span>
        {sp && <span className={`spc spc-${sp.status}`}> {sp.dist}/{sp.req} nm behind {sp.lead_cs}</span>}
      </div>
    )
  }
  return (
    <div className="detail">
      <h3>ARRIVALS (by ETA)</h3>
      {arr.length === 0 && <div className="small dim">No arrivals with an ETA yet.</div>}
      {arr.map((t, i) => strip(t, i, true))}
      <h3>DEPARTURES</h3>
      {dep.length === 0 && <div className="small dim">None.</div>}
      {dep.map((t, i) => strip(t, i, false))}
    </div>
  )
}