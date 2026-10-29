"""Single-aircraft resolution options, each simulated against the intruder AND all other traffic."""
from __future__ import annotations

import hashlib

import numpy as np

from app.core import phraseology as ph
from app.core.conflict import eligible, grid, minima, profile_of, straight_xy

NO_MANEUVER = {"FINAL", "LANDING_ROLL", "TAKEOFF_ROLL", "LINEUP", "GO_AROUND"}


def _path(s, ts, p, hdg=None, gs=None, level=None):
    if hdg is None and gs is None:
        x, y = straight_xy(s, ts)
    else:
        fine = np.arange(0.0, ts[-1] + 1.0, 1.0)
        trk0 = s["trk"]
        if hdg is None:
            ang = np.full(fine.shape, np.radians(trk0))
        else:
            delta = ((hdg - trk0 + 180.0) % 360.0) - 180.0
            turned = np.clip((fine - p.pilot_delay_s) * p.std_turn_dps, 0.0, abs(delta)) * np.sign(delta)
            ang = np.radians(trk0 + turned)
        g0 = s["gs"]
        spd = np.full(fine.shape, g0) if gs is None else g0 + np.clip(fine - p.pilot_delay_s, 0.0, abs(gs - g0)) * np.sign(gs - g0)
        vx, vy = spd / 3600.0 * np.sin(ang), spd / 3600.0 * np.cos(ang)
        cx = np.concatenate([[0.0], np.cumsum((vx[:-1] + vx[1:]) / 2.0)])
        cy = np.concatenate([[0.0], np.cumsum((vy[:-1] + vy[1:]) / 2.0)])
        x, y = np.interp(ts, fine, s["x"] + cx), np.interp(ts, fine, s["y"] + cy)
    if level is None:
        z = profile_of(s, ts, p)
    else:
        alt = s["alt"]
        rate = (p.climb_fpm if level > alt else p.descend_fpm) / 60.0
        moved = np.clip(ts - p.pilot_delay_s, 0.0, None) * rate
        z = alt + np.sign(level - alt) * np.minimum(moved, abs(level - alt))
    return x, y, z


def _ratio(path, other, hmin, vmin):
    h, dz = np.hypot(path[0] - other[0], path[1] - other[1]), np.abs(path[2] - other[2])
    r = np.maximum(h / hmin, dz / vmin)
    k = int(r.argmin())
    return float(r[k]), float(h[k]), float(dz[k]), k


def _candidates(own, intr, elev_ft, p):
    out, alt, trk = [], own["alt"], own["trk"]
    if alt - elev_ft >= 1000:
        for d in (-30, -20, 20, 30):
            h = (int(round(((trk + d) % 360) / 5.0) * 5) % 360) or 360
            delta = ((h - trk + 180.0) % 360.0) - 180.0
            out.append({"kind": "heading", "value": h, "delta": delta, "cost": abs(delta) / 10.0 * 0.6, "kw": {"hdg": float(h)}})
    if alt - elev_ft >= p.min_vector_alt_agl_ft:
        base = round(alt / 1000.0)
        for k in (-3, -2, -1, 0, 1, 2, 3):
            tgt = (base + k) * 1000.0
            if abs(tgt - alt) < 300 or tgt < elev_ft + p.min_vector_alt_agl_ft or tgt > p.max_level_ft:
                continue
            out.append({"kind": "level", "value": tgt, "cost": abs(tgt - alt) / 1000.0, "kw": {"level": tgt}})
    dtrk = abs(((trk - intr["trk"] + 180.0) % 360.0) - 180.0)
    if dtrk < 40 and own["gs"] > 200:
        u = (np.sin(np.radians(intr["trk"])), np.cos(np.radians(intr["trk"])))
        if (own["x"] - intr["x"]) * u[0] + (own["y"] - intr["y"]) * u[1] < 0:      # own is behind the intruder
            for d in (20, 30):
                out.append({"kind": "speed", "value": d, "cost": d / 20.0, "kw": {"gs": own["gs"] - d}})
    return out


def resolve(conf, by_hex, rows, p, elev_ft, transition_ft, max_options=3) -> list[dict]:
    A, B = by_hex[conf["a"]], by_hex[conf["b"]]
    ts = grid(p, extra=60.0)
    others = [r for r in rows if r["hex"] not in (A["hex"], B["hex"]) and eligible(r, p)]
    op = [_path(r, ts, p) for r in others]
    idx = [i for i, t in enumerate(ts) if t <= 120.0 and abs(t % 10.0) < 1e-6]
    good, bad = [], []
    for own, intr in ((A, B), (B, A)):
        if own.get("gnd") or own.get("phase") in NO_MANEUVER:
            continue
        hmin, vmin = minima(own, intr, p)
        ip, base = _path(intr, ts, p), _path(own, ts, p)
        mins = [minima(own, r, p) for r in others]
        busy = {i for i, o in enumerate(op) if _ratio(base, o, *mins[i])[0] < 1.0}
        for c in _candidates(own, intr, elev_ft, p):
            path = _path(own, ts, p, **c["kw"])
            ratio, h, dz, _ = _ratio(path, ip, hmin, vmin)
            side = sum(1 for i, o in enumerate(op) if i not in busy and _ratio(path, o, *mins[i])[0] < 1.0)
            text, short = ph.build_instruction(c, own, intr, transition_ft)
            ok = ratio >= p.resolution_margin and side == 0
            opt = {
                "id": "ADV-" + hashlib.sha1(f"{conf['key']}|{own['hex']}|{c['kind']}|{c['value']}".encode()).hexdigest()[:10],
                "key": conf["key"], "hex": own["hex"], "cs": ph.short_cs(own), "kind": c["kind"], "value": c["value"],
                "delta": c.get("delta"), "text": text, "short": short, "resolved": ok,
                "min_h": round(h, 1), "min_v": round(dz), "margin": round(ratio, 2), "side_effects": side,
                "cost": round(c["cost"] + (50.0 if own.get("pri", 3) < 3 else 0.0), 2),
                "path": [[round(float(path[0][i]), 2), round(float(path[1][i]), 2)] for i in idx],
            }
            (good if ok else bad).append(opt)
    if good:
        return sorted(good, key=lambda o: o["cost"])[:max_options]
    return sorted(bad, key=lambda o: -o["margin"])[:2]