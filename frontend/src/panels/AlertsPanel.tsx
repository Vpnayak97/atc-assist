import { postJSON } from '../api/client'
import { useStore } from '../state/store'

export default function AlertsPanel() {
  const ops = useStore((s) => s.ops)
  const select = useStore((s) => s.select)
  const list = (ops?.alerts ?? []).filter((a) => !a.cleared)
  return (
    <div className="detail">
      <h3>ALERTS {list.length ? `(${list.length})` : ''}</h3>
      {list.length === 0 && <div className="small dim">No active alerts.</div>}
      {list.map((a) => (
        <div key={a.id} className={`alert sev-${a.severity}${a.acknowledged ? ' acked' : ''}`} onClick={() => select(a.flights[0] ?? null)}>
          <span className="sevtag">{a.type === 'EMERGENCY' ? 'EMERGENCY' : a.severity}</span> {a.text}
          {!a.acknowledged && (
            <button onClick={(e) => { e.stopPropagation(); postJSON(`/api/alerts/${encodeURIComponent(a.id)}/ack`, {}).catch(() => {}) }}>ACK</button>
          )}
        </div>
      ))}
    </div>
  )
}