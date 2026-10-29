import { announcer } from '../voice/announcer'
import { useStore } from '../state/store'
import type { Layers } from '../state/store'

const LAYERS: [keyof Layers, string][] = [
  ['rings', 'RANGE RINGS'], ['spokes', 'BEARING SPOKES'], ['runways', 'RUNWAYS'], ['labels', 'FULL LABELS'],
  ['vectors', 'PREDICTED TRACK'], ['trails', 'TRAILS'], ['spacing', 'WAKE SPACING'],
]

export default function ControlPanel() {
  const { rangeNm, stepRange, layers, toggleLayer, health, ptlMin, setPtl, tool, setTool, voice, setVoice } = useStore()
  const active = health?.providers.filter((p) => p.ok).map((p) => p.name).join(', ') || 'none'
  return (
    <div className="control">
      <h3>MAP</h3>
      <div className="row">RANGE <button onClick={() => stepRange(-1)}>−</button><span>{rangeNm} nm</span><button onClick={() => stepRange(1)}>+</button></div>
      <div className="row" style={{ marginTop: 6 }}>PTL
        {[1, 2, 3].map((m) => <button key={m} className={ptlMin === m ? 'toggle on' : ''} onClick={() => setPtl(m)}>{m}m</button>)}
      </div>
      <h3>LAYERS</h3>
      {LAYERS.map(([k, label]) => <button key={k} className={`toggle ${layers[k] ? 'on' : ''}`} onClick={() => toggleLayer(k)}>{label}</button>)}
      <h3>TOOLS</h3>
      <button className={`toggle ${tool === 'measure' ? 'on' : ''}`} onClick={() => setTool(tool === 'measure' ? 'none' : 'measure')}>DIST / BRG</button>
      <div className="small dim">Click two aircraft or points on the radar.</div>
      <h3>VOICE</h3>
      <button className={`toggle ${voice.enabled ? 'on' : ''}`}
        onClick={() => { const on = !voice.enabled; setVoice({ enabled: on }); announcer.setSettings({ ...voice, enabled: on }); if (on) announcer.test() }}>
        {voice.enabled ? 'VOICE ON' : 'VOICE OFF'}
      </button>
      {(['conflicts', 'instructions', 'emergencies'] as const).map((k) => (
        <button key={k} className={`toggle ${voice[k] ? 'on' : ''}`} onClick={() => setVoice({ [k]: !voice[k] })}>{k.toUpperCase()}</button>
      ))}
      <h3>SOURCE</h3>
      <div className="small">{active}</div>
    </div>
  )
}