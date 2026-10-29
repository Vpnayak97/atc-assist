"""Pure geometry. Aviation units: nm, ft, kt, degrees. Works on scalars and numpy arrays."""
from __future__ import annotations

import numpy as np

EARTH_RADIUS_NM = 3440.065
FT_PER_NM = 6076.12


def wrap360(a):
    return np.asarray(a, dtype=float) % 360.0


def wrap180(a):
    return (np.asarray(a, dtype=float) + 180.0) % 360.0 - 180.0


def angle_diff(a, b):
    """Smallest signed difference a - b in degrees, in [-180, 180)."""
    return wrap180(np.asarray(a, dtype=float) - np.asarray(b, dtype=float))


def distance_nm(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dl = np.radians(lon2) - np.radians(lon1)
    h = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_NM * np.arcsin(np.sqrt(np.clip(h, 0.0, 1.0)))


def bearing_deg(lat1, lon1, lat2, lon2):
    """Initial true bearing from point 1 to point 2, 0..360."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dl = np.radians(lon2) - np.radians(lon1)
    y = np.sin(dl) * np.cos(p2)
    x = np.cos(p1) * np.sin(p2) - np.sin(p1) * np.cos(p2) * np.cos(dl)
    return wrap360(np.degrees(np.arctan2(y, x)))


def destination(lat, lon, bearing, dist_nm):
    """Point reached from (lat, lon) along a great circle."""
    d = np.asarray(dist_nm, dtype=float) / EARTH_RADIUS_NM
    th = np.radians(bearing)
    p1, l1 = np.radians(lat), np.radians(lon)
    p2 = np.arcsin(np.sin(p1) * np.cos(d) + np.cos(p1) * np.sin(d) * np.cos(th))
    l2 = l1 + np.arctan2(np.sin(th) * np.sin(d) * np.cos(p1), np.cos(d) - np.sin(p1) * np.sin(p2))
    return np.degrees(p2), wrap180(np.degrees(l2))


def dead_reckon(lat, lon, track_deg, gs_kt, dt_s):
    """Advance a position along its track at ground speed for dt_s seconds."""
    return destination(lat, lon, track_deg, np.asarray(gs_kt, dtype=float) * np.asarray(dt_s, dtype=float) / 3600.0)


def to_xy_nm(lat, lon, lat0, lon0):
    """Azimuthal equidistant projection about (lat0, lon0): x east, y north, in nm.
    Exact for range and bearing from the centre."""
    d = distance_nm(lat0, lon0, lat, lon)
    b = np.radians(bearing_deg(lat0, lon0, lat, lon))
    return d * np.sin(b), d * np.cos(b)


def from_xy_nm(x, y, lat0, lon0):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    d = np.hypot(x, y)
    b = np.degrees(np.arctan2(x, y))
    return destination(lat0, lon0, b, d)


def runway_frame(lat, lon, thr_lat, thr_lon, heading_deg):
    """Position relative to a runway threshold.
    along_nm: positive in the landing direction (negative = on the approach side).
    cross_nm: positive to the right of the landing direction."""
    x, y = to_xy_nm(lat, lon, thr_lat, thr_lon)
    h = np.radians(heading_deg)
    along = x * np.sin(h) + y * np.cos(h)
    cross = x * np.cos(h) - y * np.sin(h)
    return along, cross