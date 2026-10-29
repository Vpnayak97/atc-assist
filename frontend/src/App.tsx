import { useEffect } from 'react'
import { startSocket } from './api/socket'
import RadarCanvas from './radar/RadarCanvas'
import ControlPanel from './panels/ControlPanel'
import FlightList from './panels/FlightList'
import FlightDetail from './panels/FlightDetail'
import AIPanel from './panels/AIPanel'
import AlertsPanel from './panels/AlertsPanel'
import ConflictPanel from './panels/ConflictPanel'
import StripsPanel from './panels/StripsPanel'
import WeatherPanel from './panels/WeatherPanel'
import SequencePanel from './panels/SequencePanel'
import RunwayPanel from './panels/RunwayPanel'
import StatusBar from './components/StatusBar'
import { announcer } from './voice/announcer'
import { useStore } from './state/store'
import type { Tab } from './state/store'

const TABS: [Tab, string][] = [
  ['flight', 'FLIGHT'],
  ['seq', 'SEQ'],
  ['rwy', 'RWY'],
  ['strips', 'STRIPS'],
  ['list', 'LIST'],
  ['ai', 'AI'],
  ['wx', 'WX'],
]

export default function App() {
  const { tab, setTab, voice } = useStore()

  useEffect(() => startSocket(), [])

  useEffect(
    () =>
      useStore.subscribe((s, p) => {
        if (s.ops && s.ops !== p.ops) announcer.onOps(s.ops)
      }),
    []
  )

  useEffect(() => {
    announcer.setSettings(voice)
  }, [voice])

  return (
    <div className="app">
      <StatusBar />
      <div className="main">
        <ControlPanel />
        <div className="radar">
          <RadarCanvas />
        </div>
        <div className="side">
          <div className="opsbox">
            <AlertsPanel />
            <ConflictPanel />
          </div>
          <div className="tabs">
            {TABS.map(([k, l]) => (
              <button
                key={k}
                className={tab === k ? 'on' : ''}
                onClick={() => setTab(k)}
              >
                {l}
              </button>
            ))}
          </div>
          <div className="tabbody">
            {tab === 'flight' && <FlightDetail />}
            {tab === 'seq' && <SequencePanel />}
            {tab === 'rwy' && <RunwayPanel />}
            {tab === 'strips' && <StripsPanel />}
            {tab === 'list' && <FlightList />}
            {tab === 'ai' && <AIPanel />}
            {tab === 'wx' && <WeatherPanel />}
          </div>
        </div>
      </div>
    </div>
  )
}