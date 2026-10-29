from __future__ import annotations

from collections import deque
from typing import Optional

from app.config import Settings
from app.core import geo
from app.providers.merger import Merged, pos_time
from app.schemas.aircraft import Track
from app.schemas.runway import Airport


class Tracker:
    """Live state store: one Track per ICAO hex plus a short history ring."""

    def __init__(self, airport: Airport, settings: Settings):
        self.airport, self.settings = airport, settings
        self.tracks: dict[str, Track] = {}
        self.history: dict[str, deque] = {}

    def update(self, merged: list[Merged], now: float) -> int:
        a, new = self.airport, 0
        for m in merged:
            s = m.sample
            t = self.tracks.get(s.hex)
            if t is None:
                t = Track(hex=s.hex, sample=s)
                self.tracks[s.hex] = t
                self.history[s.hex] = deque(maxlen=60)
                new += 1
            t.sample = s
            t.callsign = s.callsign or t.callsign
            t.type = s.type or t.type
            t.quality, t.position_age_s, t.sources_agreeing = m.quality, m.position_age_s, m.sources_agreeing
            t.last_update = now
            t.dist_nm = float(geo.distance_nm(a.lat, a.lon, s.lat, s.lon))
            t.bearing_from_airport = float(geo.bearing_deg(a.lat, a.lon, s.lat, s.lon))
            t.agl_ft = 0.0 if s.on_ground else (s.alt_baro_ft - a.elev_ft if s.alt_baro_ft is not None else None)

            h = self.history[s.hex]
            pt = pos_time(s)
            if not h or pt > h[-1][0] + 0.01:      # skip repeats of the same fix (np.interp needs increasing x)
                h.append((pt, s.lat, s.lon, s.alt_baro_ft, s.gs_kt, s.track_deg, s.vrate_fpm))
        return new

    def prune(self, now: float) -> list[str]:
        gone = []
        for hx, t in self.tracks.items():
            limit = self.settings.stale_drop_ground_s if t.sample.on_ground else self.settings.stale_drop_s
            if now - t.last_update > limit:
                gone.append(hx)
        for hx in gone:
            self.tracks.pop(hx, None)
            self.history.pop(hx, None)
        return gone

    def last_samples(self) -> dict:
        return {hx: t.sample for hx, t in self.tracks.items()}

    def get(self, hx: str) -> Optional[Track]:
        return self.tracks.get(hx.lower())