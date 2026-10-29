import { postJSON } from '../api/client'
import { useStore } from '../state/store'
import Badge from '../components/Badge'

const act = (id: string, what: 'approve' | 'reject') => postJSON(`/api/advisories/${id}/${what}`, {}).catch(() => {})

export default function ConflictPanel() {
  const ops = useStore((s) => s.ops)
  const setPreview = useStore((s) => s.setPreview)
  if (!ops) return null
  return (
    <div className="detail">
      <h3>CONFLICTS &amp; ADVISORIES</h3>
      {ops.conflicts.length === 0 && <div className="small dim">No predicted conflicts (180 s lookahead, 5 nm / 1000 ft).</div>}
      {ops.conflicts.map((c) => (
        <div key={c.key} className="card">
          <div><Badge text={c.sev} tone={c.sev === 'WARNING' ? 'bad' : 'warn'} /> {c.ca} / {c.cb}
            {c.issued && <Badge text="INSTRUCTION ISSUED" tone="ok" />}</div>
          <div className="small dim">{c.los ? 'loss of separation now' : `in ${Math.round(c.t_viol)} s`} · closest {c.h_min.toFixed(1)} nm / {Math.round(c.v_min)} ft</div>
          {ops.advisories.filter((a) => a.key === c.key).map((a) => (
            <div key={a.id} className="adv" onMouseEnter={() => setPreview(a.id)} onMouseLeave={() => setPreview(null)}>
              <div>{a.text}</div>
              <div className="small dim">
                {a.resolved ? `clears to ${a.min_h} nm / ${a.min_v} ft` : 'DOES NOT FULLY CLEAR: controller judgement'} · disruption {a.cost}
              </div>
              {a.status === 'PROPOSED'
                ? <><button onClick={() => act(a.id, 'approve')}>APPROVE</button><button onClick={() => act(a.id, 'reject')}>REJECT</button></>
                : <Badge text="APPROVED (SIMULATED)" tone="ok" />}
            </div>
          ))}
        </div>
      ))}
      <h3>INSTRUCTION LOG</h3>
      {ops.issued.length === 0 && <div className="small dim">Nothing issued.</div>}
      {ops.issued.slice(0, 6).map((i) => (
        <div key={i.id} className="small">{new Date(i.at * 1000).toISOString().slice(11, 19)} <Badge text="SIMULATED" /> {i.short}</div>
      ))}
    </div>
  )
}