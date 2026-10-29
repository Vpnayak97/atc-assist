import { useEffect, useState } from 'react'
import { getJSON } from '../api/client'
import Badge from '../components/Badge'

interface St {
  name: string
  loaded: boolean
  source: string
  version: string | null
  reason: string | null
}

interface Info {
  models: Record<string, St>
  notes: string[]
  cards: Record<string, any>
}

const TITLES: Record<string, string> = {
  vertical: 'M1 Vertical profile (altitude at +30/+60 s)',
  eta: 'M2 Landing ETA with P10-P90 band',
  anomaly: 'M3 Unusual approach (secondary signal)',
}

export default function AIPanel() {
  const [info, setInfo] = useState<Info | null>(null)

  useEffect(() => {
    const load = () => getJSON<Info>('/api/models').then(setInfo).catch(() => {})
    load()
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [])

  if (!info) return <div className="detail dim">Loading model status…</div>

  const vc = info.cards.trajectory_vertical
  const ec = info.cards.eta

  return (
    <div className="detail">
      <h3>AI MODELS</h3>

      {Object.entries(info.models).map(([k, m]) => (
        <div key={k} style={{ marginBottom: 8 }}>
          <div>
            <Badge text={m.loaded ? 'ML' : 'FALLBACK'} tone={m.loaded ? 'ok' : 'warn'} />{' '}
            {TITLES[k]}
          </div>
          <div className="small dim">
            {m.version ?? 'physics only'}
            {m.reason ? ` · ${m.reason}` : ''}
          </div>
        </div>
      ))}

      {vc?.altitude_mae_ft?.LFPG_60s && (
        <div className="small">
          M1 held-out altitude error at +60 s (LFPG):{' '}
          {vc.altitude_mae_ft.LFPG_60s.join(' → ')} ft.
        </div>
      )}

      <div className="small dim">
        Horizontal ML did not beat physics, so position is dead reckoning.
      </div>

      {ec && (
        <div className="small">
          M2 held-out ETA error (physics → hybrid) is in model_cards.json; the hybrid uses physics inside 5 nm.
        </div>
      )}

      <div className="small dim">
        M3 numbers are withheld until re-evaluated on the arrivals-only filter.
      </div>

      {info.notes.map((n) => (
        <div key={n} className="small" style={{ color: 'var(--warn)' }}>
          {n}
        </div>
      ))}
    </div>
  )
}