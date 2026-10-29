from __future__ import annotations

from app.core import runway_occupancy as ro
from app.core.phraseology import spell
from app.schemas.alert import AlertType, Severity


class RunwayService:
    def __init__(self, p, airport, geom, audit, alerts):
        self.p, self.airport, self.geom, self.audit, self.alerts = p, airport, geom, audit, alerts
        self.closed: set[str] = set()
        self.crossing = geom.crossing_pairs()

    def set_closed(self, rid: str, closed: bool, now: float) -> bool:
        if rid not in {rw.id for rw in self.airport.runways}:
            return False
        (self.closed.add if closed else self.closed.discard)(rid)
        self.audit.log("runway_closed" if closed else "runway_reopened", {"runway": rid}, now)
        return True

    def update(self, rows, now, observed):
        claims = ro.build_claims(rows, self.geom, self.p.rot_s, observed)
        conflicts = ro.find_conflicts(claims, self.crossing)
        for c in conflicts:
            key = f"OCC:{c['runway']}:{'|'.join(sorted((c['a'], c['b'])))}"
            self.alerts.raise_(key, AlertType.RUNWAY_OCCUPANCY, Severity(c["sev"]), [c["a"], c["b"]],
                               f"RWY {c['runway']}: {c['ca']} and {c['cb']} overlap on the runway in {c['t']} s", now,
                               {"speech": f"Runway conflict. {spell(c['runway'].split('/')[0])} overlap in {c['t']} seconds."})
        for r in rows:
            if not r["gnd"] and r.get("rwy") and r["phase"] == "FINAL" and self.geom.runway_of(r["rwy"]) in self.closed:
                name = r.get("callsign") or r["hex"].upper()
                self.alerts.raise_(f"CLSD:{r['hex']}", AlertType.RUNWAY_OCCUPANCY, Severity.WARNING, [r["hex"]],
                                   f"{name} is on final to CLOSED runway {r['rwy']}", now,
                                   {"speech": f"Warning. {name} on final to closed runway {spell(r['rwy'])}."})
        runways = [{"id": rw.id, "closed": rw.id in self.closed,
                    "status": ro.status_for(rw.id, claims[rw.id], self.closed), "claims": claims[rw.id]}
                   for rw in self.airport.runways]
        return runways, conflicts