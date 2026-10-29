import type { Ops, VoiceSettings } from '../state/types'

type Prio = 0 | 1 | 2 | 3 // 0 emergency, 1 warning, 2 approved instruction, 3 other

interface Item {
  key: string
  text: string
  prio: Prio
  at: number
}

const RANK: Record<string, number> = {
  ADVISORY: 1,
  CAUTION: 2,
  WARNING: 3,
}

class Announcer {
  settings: VoiceSettings = {
    enabled: false,
    conflicts: true,
    instructions: true,
    emergencies: true,
  }

  private q: Item[] = []
  private cur: { prio: Prio } | null = null
  private seen = new Map<string, { rank: number; spokenAt: number }>()
  private active = new Map<string, string | undefined>() // alert id -> clear speech, for spoken alerts
  private issuedSeen = new Set<string>()
  private primed = false

  setSettings(v: VoiceSettings) {
    this.settings = v
    if (!v.enabled) {
      this.q = []
      if ('speechSynthesis' in window) window.speechSynthesis.cancel()
    }
  }

  test() {
    this.enqueue({
      key: 'test',
      text: 'Voice announcements enabled.',
      prio: 3,
      at: Date.now(),
    })
  }

  onOps(ops: Ops) {
    const now = Date.now()
    const s = this.settings

    if (!this.primed) {
      ops.issued.forEach((i) => this.issuedSeen.add(i.id))
      this.primed = true
    }

    const live = new Set<string>()

    for (const a of ops.alerts) {
      if (a.cleared) continue

      live.add(a.id)

      const emg = a.type === 'EMERGENCY'
      const rank = RANK[a.severity] ?? 1
      const prev = this.seen.get(a.id)
      let speak = false

      if (!a.acknowledged) {
        if (!prev) speak = rank >= 2
        else if (rank > prev.rank) speak = true
        else if (
          rank === 3 &&
          !a.meta.issued &&
          now - prev.spokenAt > (emg ? 90000 : 30000)
        ) {
          speak = true
        }
      }

      const allowed = emg ? s.emergencies : s.conflicts

      if (speak && allowed && a.meta.speech) {
        this.enqueue({
          key: a.id,
          text: a.meta.speech,
          prio: emg ? 0 : rank === 3 ? 1 : 3,
          at: now,
        })
        this.active.set(a.id, a.meta.clear_speech)
      }

      this.seen.set(a.id, {
        rank: Math.max(rank, prev?.rank ?? 0),
        spokenAt: speak ? now : prev?.spokenAt ?? 0,
      })
    }

    for (const [id, clear] of this.active) {
      if (live.has(id)) continue

      this.active.delete(id)
      this.seen.delete(id)

      if (clear && s.conflicts) {
        this.enqueue({
          key: id + ':clear',
          text: clear,
          prio: 3,
          at: now,
        })
      }
    }

    for (const i of ops.issued) {
      if (this.issuedSeen.has(i.id)) continue

      this.issuedSeen.add(i.id)

      if (s.instructions) {
        this.enqueue({
          key: i.id,
          text: i.text,
          prio: 2,
          at: now,
        })
      }
    }
  }

  private enqueue(item: Item) {
    if (!this.settings.enabled || !('speechSynthesis' in window)) return

    this.q = this.q.filter((x) => x.key !== item.key)
    this.q.push(item)
    this.q.sort((a, b) => a.prio - b.prio || a.at - b.at)
    this.q = this.q.slice(0, 3) // never build a backlog: lowest priorities are dropped

    if (this.cur && item.prio <= 1 && this.cur.prio > item.prio) {
      window.speechSynthesis.cancel()
    }

    this.pump()
  }

  private pump() {
    if (this.cur || !this.settings.enabled) return

    const item = this.q.shift()
    if (!item) return

    const u = new SpeechSynthesisUtterance(item.text)
    u.rate = 0.98

    const voices = window.speechSynthesis.getVoices()
    const v =
      voices.find((x) => x.lang === 'en-IN') ??
      voices.find((x) => x.lang.startsWith('en-GB')) ??
      voices.find((x) => x.lang.startsWith('en'))

    if (v) u.voice = v

    this.cur = { prio: item.prio }

    const done = () => {
      this.cur = null
      this.pump()
    }

    u.onend = done
    u.onerror = done

    window.speechSynthesis.speak(u)
  }
}

export const announcer = new Announcer()