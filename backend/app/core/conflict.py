"""State-based conflict detection with intent altitude. Rows are the 1 Hz LiveState dicts (nm x/y, ft, kt)."""
from __future__ import annotations

import numpy as np


def grid(p, extra: float = 0.0):
    return np.arange(0.0, p.conflict_lookahead_s + extra + 1e-9, p.conflict_step_s)


def eligible(s: dict, p) -> bool:
    return (not s.get("gnd") and s.get("gs") is not None and s.get("trk") is not None
            and s.get("alt") is not None and (s.get("age") or 0.0) <= p.max_conflict_age_s)


def altitude_profile(alt, vr, sel, ts, vert_extrap_s: float):
    ts = np.asarray(ts, dtype=float)
    vr = float(vr or 0.0)
    if abs(vr) < 150.0:
        return np.full(ts.shape, float(alt))
    if sel is not None and (sel - alt) * vr > 0:               # heading for the selected altitude, then level
        raw = alt + vr * ts / 60.0
        return np.minimum(raw, sel) if vr > 0 else np.maximum(raw, sel)
    return alt + vr * np.minimum(ts, vert_extrap_s) / 60.0     # intent unknown: continue briefly, then level


def straight_xy(s: dict, ts):
    v, a = s["gs"] / 3600.0, np.radians(s["trk"])
    return s["x"] + v * np.sin(a) * ts, s["y"] + v * np.cos(a) * ts


def profile_of(s: dict, ts, p):
    return altitude_profile(s["alt"], s.get("vr"), s.get("sel"), ts, p.vert_extrap_s)


def minima(a: dict, b: dict, p) -> tuple[float, float]:
    terminal = bool(p.use_terminal_minima) and a["dist"] < p.terminal_radius_nm and b["dist"] < p.terminal_radius_nm
    return (p.radar_sep_terminal_nm if terminal else p.radar_sep_nm), p.vertical_sep_ft


def severity_for(t_viol: float, los_now: bool, p) -> str:
    if los_now or t_viol <= p.conflict_warn_s:
        return "WARNING"
    return "CAUTION" if t_viol <= p.conflict_caution_s else "ADVISORY"


def detect(states: list[dict], p) -> list[dict]:
    el = [s for s in states if eligible(s, p)]
    n = len(el)
    if n < 2:
        return []
    ts = grid(p)
    X, Y, Z = np.empty((n, len(ts))), np.empty((n, len(ts))), np.empty((n, len(ts)))
    for i, s in enumerate(el):
        X[i], Y[i] = straight_xy(s, ts)
        Z[i] = profile_of(s, ts, p)
    dist = np.array([s["dist"] for s in el], dtype=float)
    I, J = np.triu_indices(n, 1)
    h = np.hypot(X[I] - X[J], Y[I] - Y[J])
    dz = np.abs(Z[I] - Z[J])
    term = bool(p.use_terminal_minima) & (dist[I] < p.terminal_radius_nm) & (dist[J] < p.terminal_radius_nm)
    hmin = np.where(term, p.radar_sep_terminal_nm, p.radar_sep_nm)[:, None]
    vmin = float(p.vertical_sep_ft)
    viol = (h < hmin) & (dz < vmin)
    ratio = np.maximum(h / hmin, dz / vmin)
    out = []
    for k in np.flatnonzero(viol.any(axis=1)):
        first, km = int(viol[k].argmax()), int(ratio[k].argmin())
        a, b = el[I[k]], el[J[k]]
        los = bool(viol[k, 0])
        t_viol = float(ts[first])
        out.append({
            "key": "|".join(sorted((a["hex"], b["hex"]))), "a": a["hex"], "b": b["hex"],
            "t_viol": t_viol, "t_min": float(ts[km]), "h_min": float(h[k, km]), "v_min": float(dz[k, km]),
            "los": los, "sev": severity_for(t_viol, los, p),
            "hreq": float(hmin[k, 0]), "vreq": vmin, "ratio": float(ratio[k, km]),
            "ax": float(X[I[k], km]), "ay": float(Y[I[k], km]), "bx": float(X[J[k], km]), "by": float(Y[J[k], km]),
        })
    return out