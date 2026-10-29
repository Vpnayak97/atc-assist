from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.core.goaround import detect_goaround, detect_holding
from app.core.phraseology import callsign_speech, short_cs, spell
from app.core.runway_geometry import RunwayGeometry
from app.core.spacing import compute_spacing
from app.schemas.aircraft import Phase
from app.schemas.alert import AlertType, Severity
from app.services.alert_service import AlertService
from app.services.audit_service import AuditService
from app.services.conflict_service import ConflictService
from app.services.emergency_service import EmergencyService
from app.services.runway_service import RunwayService
from app.services.sequence_service import SequenceService


class OpsService:
    def __init__(self, tracker, airport, settings, sep, audit_path: Path):
        self.tracker, self.airport, self.p, self.sep = tracker, airport, settings, sep
        self.alerts, self.audit = AlertService(), AuditService(audit_path)
        self.emg = EmergencyService()
        self.conf = ConflictService(settings, airport, self.audit, self.alerts)
        self.geom = RunwayGeometry(airport)
        self.rwy = RunwayService(settings, airport, self.geom, self.audit, self.alerts)
        self.seq = SequenceService(settings, airport, self.geom, sep, self.audit)
        self.finals: dict[str, tuple[str, float]] = {}
        self.ga: dict[str, dict] = {}
        self.holds: dict[str, dict] = {}
        self.last = {"conflicts": [], "advisories": [], "spacing": [], "alerts": [], "issued": [], "finals": {},
                     "runways": [], "rw_conflicts": [], "sequence": None, "holds": [], "go_arounds": []}

    def _detectors(self, rows, now):
        a, p = self.airport, self.p
        by = {r["hex"]: r for r in rows}
        for hx in list(self.ga):
            r = by.get(hx)
            if r is None or r["gnd"] or now - self.ga[hx]["t0"] > p.go_around_hold_s:
                del self.ga[hx]
        for hx in list(self.holds):
            if hx not in by or now - self.holds[hx]["seen"] > 30:
                del self.holds[hx]
        for r in rows:
            hx = r["hex"]
            if r["gnd"] or r["alt"] is None:
                continue
            agl = r["alt"] - a.elev_ft
            hist = list(self.tracker.history.get(hx, ()))
            if hx not in self.ga and r["dist"] < 12 and agl < 4500:
                d = detect_goaround(hist, a.lat, a.lon, a.elev_ft)
                if d:
                    self.ga[hx] = {"t0": now, "rwy": self.finals.get(hx, (None, 0))[0], **d}
                    self.audit.log("go_around_detected", {"hex": hx, "cs": short_cs(r), **d}, now)
            if hx not in self.ga and r["phase"] != "FINAL" and r["dist"] < 60 and agl > 1500:
                d = detect_holding(hist)
                if d:
                    self.holds[hx] = {**d, "seen": now, "t0": self.holds.get(hx, {}).get("t0", now)}
        for hx, rec in self.ga.items():
            r, t = by[hx], self.tracker.tracks.get(hx)
            r["phase"] = "GO_AROUND"
            if t:
                t.phase = Phase.GO_AROUND
            where = f" runway {rec['rwy']}" if rec["rwy"] else ""
            self.alerts.raise_(f"GA:{hx}", AlertType.GO_AROUND, Severity.WARNING, [hx],
                               f"{short_cs(r)} GO-AROUND{where.upper()}, climbing {int(rec['climb'])} ft", now,
                               {"speech": f"Go around. {callsign_speech(r.get('callsign'), r.get('reg'), hx)}"
                                          f"{', runway ' + spell(rec['rwy']) if rec['rwy'] else ''}."})
        for hx, rec in self.holds.items():
            r, t = by[hx], self.tracker.tracks.get(hx)
            r["phase"] = "HOLDING"
            if t:
                t.phase = Phase.HOLDING
            self.alerts.raise_(f"HOLD:{hx}", AlertType.HOLDING, Severity.ADVISORY, [hx],
                               f"{short_cs(r)} holding/orbiting ({int(rec['turn'])}° turned in {int(rec['span'] / 60)} min)", now)

    def update(self, rows: list[dict], now: float) -> dict:
        for e in self.emg.scan(self.tracker):
            self.alerts.raise_(e["key"], AlertType.EMERGENCY, Severity(e["severity"]), [e["hex"]], e["text"], now,
                               {"speech": e["speech"]})
        self._detectors(rows, now)
        conflicts, advisories = self.conf.update(rows, now)
        spacing = compute_spacing(rows, self.airport, self.sep)
        for s in spacing:
            if s["status"] == "short":
                text = (f"{s['follow_cs']} is {s['dist']} NM behind {s['lead_cs']} on RWY {s['rwy']}, "
                        f"wake minimum {s['req']:.0f} NM ({s['lw']}→{s['fw']}{', assumed' if s['assumed'] else ''})")
                self.alerts.raise_(f"SPC:{s['lead']}:{s['follow']}", AlertType.SPACING, Severity.CAUTION,
                                   [s["lead"], s["follow"]], text, now,
                                   {"speech": f"Wake spacing. {s['follow_cs']} is {s['dist']} miles behind {s['lead_cs']}."})
        for r in rows:
            if r["phase"] == "FINAL" and r.get("rwy"):
                self.finals[r["hex"]] = (r["rwy"], now)
        self.finals = {h: v for h, v in self.finals.items() if now - v[1] < 1800}
        observed = dict(Counter(v[0] for v in self.finals.values()))
        runways, rw_conf = self.rwy.update(rows, now, observed)
        seq = self.seq.update(rows, now, self.ga, self.rwy.closed, observed)
        self.alerts.sweep(now)
        self.last = {"conflicts": conflicts, "advisories": advisories, "spacing": spacing,
                     "alerts": self.alerts.snapshot(), "issued": self.conf.issued[:20], "finals": observed,
                     "runways": runways, "rw_conflicts": rw_conf, "sequence": seq,
                     "holds": list(self.holds), "go_arounds": list(self.ga)}
        return self.last