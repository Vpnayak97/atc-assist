from __future__ import annotations

from app.schemas.aircraft import Track


def summarize(t: Track, now: float) -> dict:
    """Compact prediction fields for the 1 Hz push. ETA is re-based to 'now' so it counts down smoothly."""
    out: dict = {}
    e = t.predictions.get("eta")
    if e:
        el = now - e.computed_at
        out["eta"] = {
            "s": max(0, round(e.value - el)),
            "lo": None if e.lo is None else max(0, round(e.lo - el)),
            "hi": None if e.hi is None else max(0, round(e.hi - el)),
            "src": e.source,
            "phys": None if e.physics_value is None else max(0, round(e.physics_value - el)),
        }
    alts = []
    for h in (30, 60):
        v = t.predictions.get(f"vertical_h{h}")
        if v:
            alts.append({"h": h, "alt": round(v.value), "src": v.source})
    if alts:
        out["alt_pred"] = alts
    a = t.predictions.get("anomaly")
    if a:
        out["anom"] = {"flag": bool(t.anomaly), "score": round(a.value, 3)}
    return out