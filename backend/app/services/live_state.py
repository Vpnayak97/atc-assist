
from __future__ import annotations

from app.config import Settings
from app.core import geo
from app.core.motion import extrapolate, turn_rate_dps
from app.core.phase import PhaseMachine, candidate_phase
from app.core.runway_geometry import RunwayGeometry
from app.core.separation import wake_category
from app.ml.features import rel_bearing
from app.ml.explain import summarize
from app.schemas.aircraft import Phase
from app.schemas.runway import Airport
from app.services.tracker import Tracker


class LiveState:
    """1 Hz view of the tracker: extrapolated kinematics, runway assignment, phase."""

    def __init__(self, tracker: Tracker, airport: Airport, settings: Settings):
        self.tracker, self.airport, self.settings = tracker, airport, settings
        self.geom = RunwayGeometry(airport)
        self.phases = PhaseMachine()

    def airport_payload(self) -> dict:
        a = self.airport
        return {
            "icao": a.icao,
            "lat": a.lat,
            "lon": a.lon,
            "elev_ft": a.elev_ft,
            "runways": self.geom.layout(),
            "sep_nm": self.settings.radar_sep_nm,
        }

    def tick(self, now: float) -> list[dict]:
        a, out = self.airport, []
        for hx, t in list(self.tracker.tracks.items()):
            s = t.sample
            k = extrapolate(
                s,
                now,
                turn_rate_dps(self.tracker.history.get(hx, [])),
                self.settings.extrapolation_limit_s,
                a.elev_ft,
            )
            dist = float(geo.distance_nm(a.lat, a.lon, k.lat, k.lon))
            brg = float(geo.bearing_deg(a.lat, a.lon, k.lat, k.lon))
            alt = a.elev_ft if s.on_ground else k.alt_ft
            agl = 0.0 if s.on_ground else (
                None if alt is None else alt - a.elev_ft
            )
            assigned = onrw = None
            rel = None
            if k.track_deg is not None:
                rel = float(
                    rel_bearing(k.lat, k.lon, k.track_deg, a.lat, a.lon)
                )
                if s.on_ground:
                    onrw = self.geom.on_runway(k.lat, k.lon, k.track_deg)
                elif agl is not None and agl < 4000:
                    assigned = self.geom.assign_arrival(
                        k.lat, k.lon, k.track_deg
                    )
            cand = candidate_phase(
                on_ground=s.on_ground,
                gs_kt=k.gs_kt,
                agl_ft=agl,
                vrate_fpm=k.vrate_fpm,
                dist_nm=dist,
                rel_brg=rel,
                assigned_runway=assigned,
                on_runway=onrw,
                prev=t.phase if t.phase != Phase.UNKNOWN else Phase.CRUISE,
            )
            t.phase = self.phases.update(hx, cand)
            t.runway = assigned or onrw
            t.dist_nm, t.bearing_from_airport, t.agl_ft = dist, brg, agl
            x, y = geo.to_xy_nm(k.lat, k.lon, a.lat, a.lon)
            out.append({
                "hex": hx,
                "callsign": t.callsign,
                "type": t.type,
                "reg": s.registration,
                "lat": round(k.lat, 5),
                "lon": round(k.lon, 5),
                "x": round(float(x), 3),
                "y": round(float(y), 3),
                "alt": None if alt is None else round(alt),
                "gs": None if k.gs_kt is None else round(k.gs_kt),
                "trk": None if k.track_deg is None else round(k.track_deg, 1),
                "vr": None if k.vrate_fpm is None else round(k.vrate_fpm),
                "sq": s.squawk,
                "phase": t.phase.value,
                "rwy": t.runway,
                "dist": round(dist, 1),
                "brg": round(brg, 1),
                "gnd": s.on_ground,
                "q": t.quality,
                "age": round(k.age_s, 1),
                "stale": k.stale,
                "pri": int(t.priority),
                "emg": t.emergency,
                "sel": s.sel_alt_ft,
                "wake": wake_category(t.type),
                "src": s.source,
                "pred": summarize(t, now),
            })
        self.phases.forget_except(self.tracker.tracks.keys())
        return out
