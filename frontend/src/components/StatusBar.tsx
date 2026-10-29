
import { useEffect, useState } from 'react'

import { useStore } from '../state/store'
import Badge from './Badge'

export default function StatusBar() {
  const { connected, health, airport, tracks } = useStore()
  const [now, setNow] = useState(new Date())
  useEffect(() => { const id = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(id) }, [])
  return (
    <div className="statusbar">
      <strong>ATC-Assist</strong>
      <span>{airport?.icao ?? '----'}</span>
      <span>{tracks.length} tracks</span>
      <Badge text={connected ? 'LINK OK' : 'LINK DOWN'} tone={connected ? 'ok' : 'bad'} />
      {health?.providers.map((p) => (
        <Badge key={p.name} text={`${p.name === 'synthetic' ? 'SIM FEED' : p.name}${p.ok ? ` ${p.n_samples}` : ''}`}
               tone={p.name === 'synthetic' ? 'warn' : p.ok ? 'ok' : p.state === 'open' ? 'bad' : 'warn'} />
      ))}
      <span>data age {health?.data_age_s ?? '--'} s</span>
      <span className="spacer" />
      <span>{now.toISOString().slice(11, 19)} UTC</span>
    </div>
  )
}
