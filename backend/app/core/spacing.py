from __future__ import annotations

from app.core import geo
from app.core.phraseology import short_cs
from app.core.separation import Separation, wake_category


def compute_spacing(rows: list[dict], airport, sep: Separation) -> list[dict]:
    groups: dict[str, list] = {}
    for r in rows:
        if r.get("gnd") or not r.get("rwy") or r["phase"] not in ("FINAL", "APPROACH"):
            continue
        try:
            e = airport.end(r["rwy"])
        except KeyError:
            continue
        along, _ = geo.runway_frame(r["lat"], r["lon"], e.thr_lat, e.thr_lon, e.heading_true)
        if float(along) <= 0.5:
            groups.setdefault(r["rwy"], []).append((float(along), r))
    out = []
    for rwy, lst in groups.items():
        lst.sort(key=lambda x: -x[0])                         # leader = closest to the threshold
        for (al, lead), (af, fol) in zip(lst, lst[1:]):
            d = al - af
            req, assumed = sep.required_nm(lead.get("type"), fol.get("type"))
            ratio = d / req
            out.append({"rwy": rwy, "lead": lead["hex"], "follow": fol["hex"], "lead_cs": short_cs(lead),
                        "follow_cs": short_cs(fol), "dist": round(d, 1), "req": req, "assumed": assumed,
                        "lw": wake_category(lead.get("type")), "fw": wake_category(fol.get("type")),
                        "status": "ok" if ratio >= 1 else "marginal" if ratio >= 0.85 else "short"})
    return out