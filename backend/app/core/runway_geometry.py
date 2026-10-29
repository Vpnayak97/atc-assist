
from __future__ import annotations

import math
from typing import Optional

from app.core import geo
from app.schemas.runway import Airport


def _ccw(a, b, c):
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])


def _seg_intersect(s1, s2):
    a, b = s1
    c, d = s2
    return _ccw(a, c, d) != _ccw(b, c, d) and _ccw(a, b, c) != _ccw(a, b, d)


class RunwayGeometry:
    """Approach funnels, runway surfaces and display layout for one airport."""

    def __init__(
        self,
        airport: Airport,
        funnel_deg: float = 10.0,
        max_final_nm: float = 20.0,
        heading_tol: float = 25.0,
    ):
        self.airport = airport
        self.funnel_tan = math.tan(math.radians(funnel_deg))
        self.max_final_nm, self.heading_tol = max_final_nm, heading_tol
        self.ends = [(rw.id, e) for rw in airport.runways for e in rw.ends]

    def assign_arrival(
        self, lat: float, lon: float, track_deg: float
    ) -> Optional[str]:
        """Runway end whose final-approach funnel contains the aircraft and which it is aligned with."""
        best, best_score = None, 1e9
        for _, e in self.ends:
            along, cross = geo.runway_frame(
                lat, lon, e.thr_lat, e.thr_lon, e.heading_true
            )
            along, cross = float(along), float(cross)
            if not (-self.max_final_nm <= along <= 1.0):
                continue
            hd = abs(float(geo.angle_diff(track_deg, e.heading_true)))
            if hd > self.heading_tol:
                continue
            if abs(cross) > 0.5 + abs(along) * self.funnel_tan:
                continue
            score = abs(cross) + 0.02 * hd
            if score < best_score:
                best, best_score = e.ident, score
        return best

    def on_runway(
        self, lat: float, lon: float, track_deg: float
    ) -> Optional[str]:
        """Runway end (aligned with the track) if the position is on a runway surface."""
        best, best_hd = None, 1e9
        for _, e in self.ends:
            length_nm = e.length_ft / geo.FT_PER_NM
            if length_nm <= 0:
                continue
            along, cross = geo.runway_frame(
                lat, lon, e.thr_lat, e.thr_lon, e.heading_true
            )
            if (
                -0.02 <= float(along) <= length_nm + 0.02
                and abs(float(cross)) <= 0.04
            ):
                hd = abs(float(geo.angle_diff(track_deg, e.heading_true)))
                if hd < best_hd:
                    best, best_hd = e.ident, hd
        return best

    def layout(self) -> list[dict]:
        a, out = self.airport, []
        for rw in a.runways:
            ends = []
            for e in rw.ends:
                x, y = geo.to_xy_nm(
                    e.thr_lat, e.thr_lon, a.lat, a.lon
                )
                ends.append({
                    "ident": e.ident,
                    "x": round(float(x), 3),
                    "y": round(float(y), 3),
                    "hdg": e.heading_true,
                })
            out.append({"id": rw.id, "ends": ends})
        return out

    def runway_of(self, ident):
        for rid, e in self.ends:
            if e.ident == ident:
                return rid
        return None

    def crossing_pairs(self) -> set:
        a, segs = self.airport, {}
        for rw in a.runways:
            if len(rw.ends) == 2:
                pts = []
                for e in rw.ends:
                    x, y = geo.to_xy_nm(
                        e.thr_lat, e.thr_lon, a.lat, a.lon
                    )
                    pts.append((float(x), float(y)))
                segs[rw.id] = (pts[0], pts[1])

        ids, out = list(segs), set()
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                if _seg_intersect(segs[ids[i]], segs[ids[j]]):
                    out.add(frozenset((ids[i], ids[j])))
        return out

    def predict_end(self, lat, lon, track_deg, observed=None, exclude=None):
        best, bs = None, 1e9
        for rid, e in self.ends:
            if exclude and rid in exclude:
                continue
            along, cross = geo.runway_frame(
                lat, lon, e.thr_lat, e.thr_lon, e.heading_true
            )
            if float(along) > 0.5:
                continue
            ad = abs(float(geo.angle_diff(track_deg, e.heading_true)))
            if ad > 50.0:
                continue
            score = abs(float(cross)) + 0.1 * ad
            if observed and observed.get(e.ident):
                score *= 0.5
            if score < bs:
                best, bs = e.ident, score
        return best

    def default_end(self, observed=None, exclude=None):
        cand = [
            e.ident
            for rid, e in self.ends
            if not (exclude and rid in exclude)
        ]
        if not cand:
            return None
        seen = [
            (observed.get(c, 0), c)
            for c in cand
            if observed and observed.get(c, 0) > 0
        ]
        return max(seen)[1] if seen else cand[0]

    def choose_end(self, lat, lon, track_deg, observed=None, exclude=None):
        return (
            self.predict_end(lat, lon, track_deg, observed, exclude)
            or self.default_end(observed, exclude)
        )
