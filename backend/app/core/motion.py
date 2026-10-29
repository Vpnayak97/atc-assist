"""Dead reckoning between fetches (direction document, section 5.1). Pure functions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core import geo
from app.schemas.aircraft import RawSample

MAX_TURN_DPS = 3.0     # standard-rate turn


@dataclass
class Kin:
    lat: float
    lon: float
    alt_ft: Optional[float]
    track_deg: Optional[float]
    gs_kt: Optional[float]
    vrate_fpm: Optional[float]
    age_s: float            # age of the underlying fix
    extrapolated_s: float   # how far we projected (capped)
    stale: bool             # fix older than the extrapolation limit


def sample_time(s: RawSample) -> float:
    return s.fetched_at - (s.seen_pos_s or 0.0)


def turn_rate_dps(history) -> float:
    """Turn rate from the last two history fixes: (pos_time, lat, lon, alt, gs, track, vrate)."""
    pts = list(history)[-2:]
    if len(pts) < 2:
        return 0.0
    a, b = pts
    dt = b[0] - a[0]
    if dt < 2.0 or dt > 60.0 or a[5] is None or b[5] is None or b[4] is None or b[4] < 40.0:
        return 0.0
    rate = float(geo.angle_diff(b[5], a[5])) / dt
    return max(-MAX_TURN_DPS, min(MAX_TURN_DPS, rate))


def extrapolate(s: RawSample, now: float, turn_rate: float = 0.0,
                limit_s: float = 30.0, floor_ft: float = 0.0) -> Kin:
    age = max(0.0, now - sample_time(s))
    dt = min(age, limit_s)
    lat, lon, track, gs = s.lat, s.lon, s.track_deg, s.gs_kt
    out_track = track
    if track is not None and gs is not None and gs > 0 and dt > 0:
        mid = track + 0.5 * turn_rate * dt                     # chord of a constant-rate turn
        la, lo = geo.dead_reckon(lat, lon, mid, gs, dt)
        lat, lon = float(la), float(lo)
        out_track = float(geo.wrap360(track + turn_rate * dt))
    alt = s.alt_baro_ft
    if alt is not None and not s.on_ground and s.vrate_fpm is not None and dt > 0:
        alt = max(floor_ft, alt + s.vrate_fpm * dt / 60.0)
    return Kin(lat, lon, alt, out_track, gs, s.vrate_fpm, age, dt, age > limit_s)