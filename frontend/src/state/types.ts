export interface Track {
  hex: string; callsign: string | null; type: string | null; reg: string | null;
  lat: number; lon: number; x: number; y: number;
  alt: number | null; gs: number | null; trk: number | null; vr: number | null; sq: string | null;
  phase: string; rwy: string | null; dist: number; brg: number; gnd: boolean;
  q: number; age: number; stale: boolean; pri: number; emg: string | null; src: string;
  sel: number | null; wake: string;
  pred?: {
    eta?: { s: number; lo: number | null; hi: number | null; src: string; phys: number | null };
    alt_pred?: { h: number; alt: number; src: string }[];
    anom?: { flag: boolean; score: number };
  };
}

export interface RunwayEnd { ident: string; x: number; y: number; hdg: number }
export interface RunwayLayout { id: string; ends: RunwayEnd[] }
export interface Airport { icao: string; lat: number; lon: number; elev_ft: number; sep_nm: number; runways: RunwayLayout[] }

export interface ProviderStatus {
  name: string; state: string; ok: boolean; last_success: number | null;
  last_error: string | null; latency_ms: number | null; n_samples: number;
}

export interface Health {
  status: string; airport: string; data_age_s: number | null;
  providers: ProviderStatus[]; last_cycle: Record<string, unknown> | null; models: Record<string, unknown>;
}

export type Sev = 'ADVISORY' | 'CAUTION' | 'WARNING';

export interface Conflict {
  key: string; a: string; b: string; ca: string; cb: string; sev: Sev; t_viol: number; t_min: number;
  h_min: number; v_min: number; los: boolean; ax: number; ay: number; bx: number; by: number;
  hreq: number; vreq: number; issued: boolean;
}

export interface Advisory {
  id: string; key: string; hex: string; cs: string; kind: 'heading' | 'level' | 'speed'; text: string; short: string;
  resolved: boolean; min_h: number; min_v: number; margin: number; cost: number;
  path: [number, number][]; status: 'PROPOSED' | 'APPROVED'; issued_at: number | null;
}

export interface Spacing {
  rwy: string; lead: string; follow: string; lead_cs: string; follow_cs: string; dist: number; req: number;
  status: 'ok' | 'marginal' | 'short'; assumed: boolean; lw: string; fw: string;
}

export interface AlertT {
  id: string; type: string; severity: Sev; flights: string[]; text: string; created_at: number;
  updated_at: number; acknowledged: boolean; cleared: boolean;
  meta: { speech?: string; clear_speech?: string; issued?: boolean };
}

export interface Issued { id: string; text: string; short: string; at: number; hex: string; cs: string }

export interface RunwayClaim {
  hex: string; cs: string; kind: 'ARR' | 'DEP'; start: number; end: number;
  conf: number; pred: boolean; on: boolean;
}

export interface RunwayState {
  id: string; closed: boolean; status: string; claims: RunwayClaim[];
}

export interface RwConflict {
  runway: string; a: string; b: string; ca: string; cb: string;
  t: number; overlap: number; sev: Sev;
}

export interface SeqEntry {
  hex: string; cs: string; type: string | null; wake: string; rwy: string; rid: string; pos: number; pri: number;
  frozen: boolean; ga: boolean; delay: number; late: boolean; eta_in: number; assigned_in: number; reason: string;
}

export interface SeqMetrics {
  n: number; total: number; fcfs_total: number; max: number; fcfs_max: number; w: number; fcfs_w: number;
}

export interface Seq {
  generated_at: number | null; solver: string; solve_ms: number; optimal: boolean;
  metrics: SeqMetrics | null; entries: SeqEntry[]; closed: string[];
}

export interface Ops {
  conflicts: Conflict[];
  advisories: Advisory[];
  spacing: Spacing[];
  alerts: AlertT[];
  issued: Issued[];
  finals: Record<string, number>;
  runways: RunwayState[];
  rw_conflicts: RwConflict[];
  sequence: Seq | null;
  holds: string[];
  go_arounds: string[];
}

export interface Pt { x: number; y: number; hex?: string }

export interface VoiceSettings {
  enabled: boolean; conflicts: boolean; instructions: boolean; emergencies: boolean;
}
