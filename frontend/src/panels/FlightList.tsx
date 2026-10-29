import { useStore } from '../state/store'

export default function FlightList() {
  const { tracks, selected, select } = useStore()
  const rows = [...tracks].sort((a, b) => a.dist - b.dist)
  return (
    <div className="flightlist">
      <table>
        <thead><tr><th>CALL</th><th>TYPE</th><th>ALT</th><th>GS</th><th>PHASE</th><th>NM</th></tr></thead>
        <tbody>
          {rows.map((t) => (
            <tr key={t.hex} className={t.hex === selected ? 'sel' : t.emg ? 'emg' : ''} onClick={() => select(t.hex)}>
              <td>{t.callsign ?? t.hex.toUpperCase()}</td>
              <td>{t.type ?? '-'}</td>
              <td>{t.gnd ? 'GND' : t.alt ?? '-'}</td>
              <td>{t.gs ?? '-'}</td>
              <td>{t.phase}{t.rwy ? ` ${t.rwy}` : ''}</td>
              <td>{t.dist}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}