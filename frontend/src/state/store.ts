import { create } from 'zustand'
import type { Airport, Health, Ops, Pt, Track, VoiceSettings } from './types'

export const RANGES = [10, 20, 30, 40, 60, 80, 120]
export interface Layers { rings: boolean; spokes: boolean; runways: boolean; labels: boolean; vectors: boolean; trails: boolean; spacing: boolean }
export type Tab = 'flight' | 'strips' | 'seq' | 'rwy' | 'list' | 'ai' | 'wx'

interface S {
  connected: boolean; airport: Airport | null; tracks: Track[]; recvAt: number; health: Health | null
  ops: Ops | null; selected: string | null; rangeNm: number; layers: Layers
  ptlMin: number; tool: 'none' | 'measure'; measure: { a: Pt | null; b: Pt | null }
  preview: string | null; voice: VoiceSettings; tab: Tab
  setConnected: (c: boolean) => void
  applySnapshot: (a: Airport, t: Track[], h: Health) => void
  applyTracks: (t: Track[]) => void
  applyOps: (o: Ops) => void
  setHealth: (h: Health) => void
  select: (hex: string | null) => void
  stepRange: (dir: 1 | -1) => void
  toggleLayer: (k: keyof Layers) => void
  setPtl: (m: number) => void
  setTool: (t: 'none' | 'measure') => void
  setMeasure: (m: { a: Pt | null; b: Pt | null }) => void
  setPreview: (id: string | null) => void
  setVoice: (v: Partial<VoiceSettings>) => void
  setTab: (t: Tab) => void
}

export const useStore = create<S>((set) => ({
  connected: false, airport: null, tracks: [], recvAt: 0, health: null, ops: null, selected: null, rangeNm: 40,
  layers: { rings: true, spokes: true, runways: true, labels: true, vectors: true, trails: true, spacing: true },
  ptlMin: 1, tool: 'none', measure: { a: null, b: null }, preview: null, tab: 'flight',
  voice: { enabled: false, conflicts: true, instructions: true, emergencies: true },
  setConnected: (connected) => set({ connected }),
  applySnapshot: (airport, tracks, health) => set({ airport, tracks, health, recvAt: performance.now() }),
  applyTracks: (tracks) => set({ tracks, recvAt: performance.now() }),
  applyOps: (ops) => set({ ops }),
  setHealth: (health) => set({ health }),
  select: (selected) => set({ selected }),
  stepRange: (dir) => set((s) => {
    const i = RANGES.indexOf(s.rangeNm)
    return { rangeNm: RANGES[Math.min(RANGES.length - 1, Math.max(0, i + dir))] }
  }),
  toggleLayer: (k) => set((s) => ({ layers: { ...s.layers, [k]: !s.layers[k] } })),
  setPtl: (ptlMin) => set({ ptlMin }),
  setTool: (tool) => set({ tool, measure: { a: null, b: null } }),
  setMeasure: (measure) => set({ measure }),
  setPreview: (preview) => set({ preview }),
  setVoice: (v) => set((s) => ({ voice: { ...s.voice, ...v } })),
  setTab: (tab) => set({ tab }),
}))