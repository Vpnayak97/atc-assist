from __future__ import annotations

import logging

import numpy as np

from app.config import Settings
from app.core import geo
from app.ml import anomaly_model, fallbacks as fb, features as F
from app.ml.eta_model import predict_eta
from app.ml.registry import Registry
from app.ml.vertical_model import predict_vertical
from app.providers.merger import pos_time
from app.schemas.aircraft import Phase, Prediction
from app.schemas.runway import Airport
from app.services.tracker import Tracker

log = logging.getLogger("atc.predict")
MIN_APPROACH_PTS = 12      # Colab used 25; live history is ~30 s cadence


def _series(hist, idx):
    pts = [(h[0], h[idx]) for h in hist if h[idx] is not None]
    return [p[0] for p in pts], [p[1] for p in pts]


class PredictionService:
    """Runs after every fetch cycle. Predictions are anchored to the fix time (computed_at)."""

    def __init__(self, reg: Registry, tracker: Tracker, airport: Airport, settings: Settings):
        self.reg, self.tracker, self.airport, self.settings = reg, tracker, airport, settings
        self.headings = F.runway_headings(airport)

    def run(self, now: float) -> None:
        tracks = [t for t in self.tracker.tracks.values() if not t.sample.on_ground]
        for fn in (self._vertical, self._eta, self._anomaly):
            try:
                fn(tracks)
            except Exception:
                log.exception("%s failed", fn.__name__)

    @staticmethod
    def _clear(t, *keys):
        for k in keys:
            t.predictions.pop(k, None)

    # ---- Model 1: altitude at +30/+60 s ------------------------------------
    def _vertical(self, tracks):
        a, rows, idx = self.airport, [], []
        for t in tracks:
            s = t.sample
            if None in (s.alt_baro_ft, s.gs_kt, s.track_deg) or t.position_age_s > 45:
                self._clear(t, "vertical_h30", "vertical_h60")
                continue
            r = F.m1_row(lat=s.lat, lon=s.lon, alt_ft=s.alt_baro_ft, on_ground=False, gs_kt=s.gs_kt,
                         track=s.track_deg, vrate_fpm=s.vrate_fpm or 0.0, ts=pos_time(s),
                         airport=a, headings=self.headings)
            if self.reg.vertical and not F.m1_in_domain(r):
                r = None                                   # outside the trained domain: physics only
            rows.append(r)
            idx.append(t)
        valid = [r for r in rows if r is not None]
        ea = predict_vertical(self.reg, valid) if valid else {}
        k = 0
        for t, r in zip(idx, rows):
            s, ts = t.sample, pos_time(t.sample)
            use = r is not None and bool(ea)
            for H in (30, 60):
                phys = fb.physics_alt(s.alt_baro_ft, s.vrate_fpm or 0.0, H, a.elev_ft)
                ml = use and H in ea
                val = phys + float(ea[H][k]) if ml else phys
                t.predictions[f"vertical_h{H}"] = Prediction(
                    kind="vertical", value=round(max(a.elev_ft, val)), unit="ft",
                    source="ml" if ml else "physics",
                    model_version=self.reg.st["vertical"].version if ml else None,
                    physics_value=round(phys), computed_at=ts)
            if r is not None:
                k += 1

    # ---- Model 2: ETA --------------------------------------------------------
    def _eta(self, tracks):
        rows, idx = [], []
        for t in tracks:
            s = t.sample
            if t.phase not in (Phase.APPROACH, Phase.FINAL, Phase.DESCENT) or None in (s.alt_baro_ft, s.gs_kt, s.track_deg):
                self._clear(t, "eta")
                continue
            hist, ts = self.tracker.history.get(s.hex, []), pos_time(s)
            tg, vg = _series(hist, 4)
            ta, va = _series(hist, 3)
            r = F.eta_row(gs_d60=F.delta_60(tg, vg, ts, s.gs_kt), agl_d60=F.delta_60(ta, va, ts, s.alt_baro_ft),
                          type_code=t.type, min_gs_kt=self.settings.min_gs_for_eta_kt,
                          lat=s.lat, lon=s.lon, alt_ft=s.alt_baro_ft, on_ground=False, gs_kt=s.gs_kt,
                          track=s.track_deg, vrate_fpm=s.vrate_fpm or 0.0, ts=ts,
                          airport=self.airport, headings=self.headings)
            if not F.eta_in_domain(r) or abs(r["rel_brg"]) > 90 or (s.vrate_fpm or 0.0) > 300:
                self._clear(t, "eta")
                continue
            rows.append(r)
            idx.append(t)
        for t, p in zip(idx, predict_eta(self.reg, rows, [pos_time(t.sample) for t in idx])):
            t.predictions["eta"] = p

    # ---- Model 3: unusual approach (secondary signal; rules arrive in Phase 5) --
    def _segment(self, hist):
        pts = [h for h in hist if None not in (h[3], h[4], h[5])]
        start = 0
        for i in range(1, len(pts)):
            if pts[i][0] - pts[i - 1][0] > 300:
                start = i
        pts = pts[start:]
        if len(pts) < MIN_APPROACH_PTS:
            return None
        a = self.airport
        ts, lat, lon = (np.array([p[i] for p in pts], dtype=float) for i in (0, 1, 2))
        alt, gs, trk = (np.array([p[i] for p in pts], dtype=float) for i in (3, 4, 5))
        vr = np.array([p[6] or 0.0 for p in pts], dtype=float)
        dist, agl = geo.distance_nm(a.lat, a.lon, lat, lon), alt - a.elev_ft
        m = (dist < 40) & (agl < 12000)
        if m.sum() < MIN_APPROACH_PTS:
            return None
        return ts[m], agl[m], trk[m], gs[m], vr[m], dist[m]

    def _anomaly(self, tracks):
        if self.reg.anomaly is None:
            return
        thr = anomaly_model.threshold(self.reg)
        for t in tracks:
            seg = self._segment(self.tracker.history.get(t.hex, []))
            if seg is None or not F.approach_segment_ok(seg[1], seg[5], MIN_APPROACH_PTS):
                self._clear(t, "anomaly")
                t.anomaly = False
                continue
            feats = {k: float(v) for k, v in F.approach_feats(*seg).items()}
            sc = anomaly_model.score(self.reg, feats)
            t.anomaly = sc < thr
            t.predictions["anomaly"] = Prediction(
                kind="anomaly", value=sc, unit="score", source="ml", model_version=self.reg.st["anomaly"].version,
                explanation=anomaly_model.outliers(self.reg, feats), computed_at=pos_time(t.sample))