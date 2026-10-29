"""Feature construction. Must reproduce the Colab features exactly (direction document, section 6.4)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core import geo
from app.schemas.runway import Airport

M1_FEATS = ["dist_nm", "rel_brg", "agl", "gs_kt", "vrate_fpm", "trk_sin", "trk_cos", "rw_off", "hour"]
M1_MAX_DIST_NM, M1_MAX_AGL_FT = 40.0, 15000.0                 # training domain of Model 1
ETA_MIN_DIST_NM, ETA_MAX_DIST_NM, ETA_MIN_AGL_FT = 2.0, 35.0, 150.0   # training domain of Model 2


def runway_headings(airport: Airport) -> np.ndarray:
    # ASSUMPTION: Colab's RW[airport] holds both ends of every runway. Confirm against the RW cell.
    return np.array([e.heading_true for rw in airport.runways for e in rw.ends], dtype=float)


def rw_off(track, headings: np.ndarray) -> np.ndarray:
    """Smallest angle between the track and any runway heading; 90 if the airport has none."""
    track = np.atleast_1d(np.asarray(track, dtype=float))
    if len(headings) == 0:
        return np.full(track.shape, 90.0)
    diff = np.abs(((track[:, None] - headings[None, :] + 180.0) % 360.0) - 180.0)
    return diff.min(axis=1)


def rel_bearing(lat, lon, track, a_lat, a_lon):
    """Bearing to the airport relative to the track, -180..180 (positive = airport to the right)."""
    brg = geo.bearing_deg(lat, lon, a_lat, a_lon)
    return ((brg - np.asarray(track, dtype=float) + 540.0) % 360.0) - 180.0


def agl_ft(alt_ft, on_ground: bool, elev_ft: float) -> float:
    return 0.0 if on_ground else float(alt_ft) - elev_ft


def delta_60(times, values, now_t: float, now_v: float) -> float:
    """Change over the last 60 s with np.interp semantics (clamped to the oldest sample),
    exactly as in Colab. `times`/`values` must include the current sample."""
    t, v = np.asarray(times, dtype=float), np.asarray(values, dtype=float)
    if len(t) == 0:
        return 0.0
    return float(now_v - np.interp(now_t - 60.0, t, v))


def _common(*, lat, lon, alt_ft, on_ground, gs_kt, track, vrate_fpm, ts, airport: Airport, headings) -> dict:
    return {
        "dist_nm": float(geo.distance_nm(airport.lat, airport.lon, lat, lon)),
        "rel_brg": float(rel_bearing(lat, lon, track, airport.lat, airport.lon)),
        "agl": agl_ft(alt_ft, on_ground, airport.elev_ft),
        "gs_kt": float(gs_kt),
        "vrate_fpm": float(vrate_fpm),
        "trk_sin": float(np.sin(np.radians(track))),
        "trk_cos": float(np.cos(np.radians(track))),
        "rw_off": float(rw_off(track, headings)[0]),
        "hour": int((ts // 3600) % 24),                        # UTC hour, as pd.to_datetime(ts, unit='s').dt.hour
    }


def m1_row(**kw) -> dict:
    row = _common(**kw)
    return {k: row[k] for k in M1_FEATS}


def m1_in_domain(row: dict) -> bool:
    return row["dist_nm"] < M1_MAX_DIST_NM and -100.0 < row["agl"] < M1_MAX_AGL_FT


def eta_row(*, gs_d60: float, agl_d60: float, type_code, min_gs_kt: float = 80.0, **kw) -> dict:
    row = _common(**kw)
    row["gs_d60"], row["agl_d60"] = float(gs_d60), float(agl_d60)
    row["phys_eta"] = row["dist_nm"] / max(row["gs_kt"], min_gs_kt) * 3600.0
    row["type"] = type_code
    return row


def eta_in_domain(row: dict) -> bool:
    return ETA_MIN_DIST_NM < row["dist_nm"] < ETA_MAX_DIST_NM and row["agl"] > ETA_MIN_AGL_FT


def eta_frame(rows: list[dict], feature_order: list[str], categories: list[str]) -> pd.DataFrame:
    """DataFrame in training column order, with type_c as a categorical on the trained categories."""
    df = pd.DataFrame(rows)
    t = df["type"].where(df["type"].isin(categories), "other")
    df["type_c"] = pd.Categorical(t, categories=categories)
    return df[feature_order]

def approach_feats(ts, agl, trk, gs, vr, dist) -> dict:
    """Identical to Colab Cell 11."""
    ts, agl, trk, gs, vr, dist = [np.asarray(x, dtype=float) for x in (ts, agl, trk, gs, vr, dist)]
    dt = ((np.diff(trk) + 180) % 360) - 180
    path = (gs[1:] * np.diff(ts) / 3600).sum()
    kmin = int(agl.argmin()); low = agl < 3000
    lvl = (np.abs(vr) < 200) & (agl > 1000) & (agl < 10000)
    dts = np.diff(ts, prepend=ts[0])
    return dict(turn_total=np.abs(dt).sum(), net_turn=abs(dt.sum()),
                path_ratio=path / max(dist[0] - dist.min(), 1.0),
                climb_after_min=agl[kmin:].max() - agl[kmin], agl_min=agl.min(),
                vr_min=vr.min(), vr_std=vr.std(),
                gs_std_low=gs[low].std() if low.sum() > 3 else 0.0,
                gs_low=np.median(gs[agl < 1500]) if (agl < 1500).sum() > 2 else np.median(gs),
                level_s=dts[lvl].sum(), dur_s=ts[-1] - ts[0], start_agl=agl[0])


def approach_segment_ok(agl, dist, min_len: int = 12) -> bool:
    """Arrival filter from Colab Cell 13 (starts high, gets low, flew toward the airport)."""
    agl, dist = np.asarray(agl, dtype=float), np.asarray(dist, dtype=float)
    if len(agl) < min_len:
        return False
    k = int(agl.argmin())
    return bool(agl[0] >= 3000 and agl.min() <= 2500 and k >= 0.2 * len(agl)
                and dist[0] >= dist[k] + 5 and dist[k] <= 12)