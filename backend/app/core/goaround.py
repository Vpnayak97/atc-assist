from __future__ import annotations

import numpy as np

from app.core import geo


def _pts(hist, window_s, need_trk=False):
    pts = [h for h in hist if h[3] is not None and (not need_trk or h[5] is not None)]
    if not pts:
        return []
    t_end = pts[-1][0]
    return [h for h in pts if t_end - h[0] <= window_s]


def detect_goaround(hist, a_lat, a_lon, elev_ft, window_s: float = 600.0):
    """hist rows: (time, lat, lon, alt_ft, gs, track, vrate). Descended low near the airport, now climbing away."""
    pts = _pts(hist, window_s)
    if len(pts) < 4:
        return None
    agl = np.array([h[3] for h in pts], dtype=float) - elev_ft
    dist = geo.distance_nm(a_lat, a_lon, np.array([h[1] for h in pts], dtype=float),
                           np.array([h[2] for h in pts], dtype=float))
    k = int(agl.argmin())
    if k >= len(pts) - 1:
        return None
    climb = float(agl[-1] - agl[k])
    vr = [h[6] or 0.0 for h in pts[-2:]]
    ok = (agl[k] < 2500 and dist[k] < 8.0 and agl[: k + 1].max() >= agl[k] + 500
          and dist[0] >= dist[k] + 2.0 and 500.0 <= climb < 5000.0 and min(vr) > 300.0)
    return {"min_agl": float(agl[k]), "climb": climb, "dist_min": float(dist[k])} if ok else None


def detect_holding(hist, window_s: float = 360.0, min_fixes: int = 6):
    pts = _pts(hist, window_s, need_trk=True)
    if len(pts) < min_fixes:
        return None
    trk = np.array([h[5] for h in pts], dtype=float)
    cum = float(np.abs(geo.angle_diff(trk[1:], trk[:-1])).sum())
    net = float(geo.distance_nm(pts[0][1], pts[0][2], pts[-1][1], pts[-1][2]))
    span = float(pts[-1][0] - pts[0][0])
    return {"turn": cum, "net": net, "span": span} if (cum >= 360.0 and net < 5.0 and span >= 150.0) else None