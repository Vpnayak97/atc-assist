from __future__ import annotations


def _claim(r, kind, start, end, conf, pred, on):
    return {"hex": r["hex"], "cs": r.get("callsign") or r["hex"].upper(), "kind": kind, "start": round(start, 1),
            "end": round(end, 1), "conf": conf, "pred": pred, "on": on, "gs": r.get("gs") or 0, "phase": r["phase"]}


def build_claims(rows, geom, rot_s, observed) -> dict:
    claims = {rw.id: [] for rw in geom.airport.runways}
    for r in rows:
        if r["gnd"]:
            if r.get("rwy") and r["phase"] in ("LINEUP", "TAKEOFF_ROLL", "LANDING_ROLL"):
                rid = geom.runway_of(r["rwy"])
                if rid is None:
                    continue
                kind, s, e = (("ARR", -5.0, 25.0) if r["phase"] == "LANDING_ROLL"
                              else ("DEP", -5.0, 30.0) if r["phase"] == "TAKEOFF_ROLL" else ("DEP", 0.0, 60.0))
                claims[rid].append(_claim(r, kind, s, e, 1.0, False, True))
            continue
        eta = ((r.get("pred") or {}).get("eta") or {}).get("s")
        if eta is None or r["phase"] in ("GO_AROUND", "HOLDING") or eta > 1800:
            continue
        end, pred = r.get("rwy"), r.get("rwy") is None
        if pred:
            if r.get("trk") is None:
                continue
            end = geom.choose_end(r["lat"], r["lon"], r["trk"], observed)
        rid = geom.runway_of(end) if end else None
        if rid is None:
            continue
        rot = float(rot_s.get(r.get("wake", "M"), 50.0))
        claims[rid].append(_claim(r, "ARR", eta - 10.0, eta + rot, 0.6 if pred else 1.0, pred, False))
    return claims


def status_for(rid, cl, closed) -> str:
    if rid in closed:
        return "CLOSED"
    on = [c for c in cl if c["on"]]
    if on:
        return "CLEARING" if any(c["phase"] == "LANDING_ROLL" and c["gs"] < 40 for c in on) else "OCCUPIED"
    return "ARRIVAL_IMMINENT" if any(c["kind"] == "ARR" and c["start"] <= 90 for c in cl) else "FREE"


def find_conflicts(claims, crossing) -> list[dict]:
    flat = [(rid, c) for rid, cl in claims.items() for c in cl]
    out = []
    for i in range(len(flat)):
        for j in range(i + 1, len(flat)):
            (ra, a), (rb, b) = flat[i], flat[j]
            if a["hex"] == b["hex"] or (ra != rb and frozenset((ra, rb)) not in crossing):
                continue
            ov = min(a["end"], b["end"]) - max(a["start"], b["start"])
            if ov <= 5.0:
                continue
            t = max(a["start"], b["start"])
            out.append({"runway": ra if ra == rb else f"{ra} x {rb}", "a": a["hex"], "b": b["hex"],
                        "ca": a["cs"], "cb": b["cs"], "t": round(max(t, 0.0)), "overlap": round(ov),
                        "sev": "WARNING" if t <= 45 else "CAUTION" if t <= 120 else "ADVISORY"})
    return out