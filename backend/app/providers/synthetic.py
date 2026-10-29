from __future__ import annotations

import time

from app.core import geo
from app.providers.base import Provider
from app.schemas.aircraft import RawSample


class Synthetic(Provider):
    """Simulated traffic that repeats every `period_s`: a head-on pair, a too-close pair on final, a 7700 climb-out.
    Enabled only by adding 'synthetic' to ATC_PROVIDER_ORDER. Tagged source='synthetic' and shown as SIM in the UI."""
    name = "synthetic"
    min_interval_s = 0.0

    def __init__(self, airport, open_after=3, probe_after_s=60.0, period_s=360.0):
        super().__init__(open_after, probe_after_s)
        self.ap, self.period, self.t0 = airport, period_s, time.time()

    async def _fetch(self, client, lat, lon, radius_nm):
        now = time.time()
        cyc, el = divmod(now - self.t0, self.period)
        cyc, ap, out = int(cyc), self.ap, []

        def add(i, cs, typ, la, lo, alt, gs, trk, vr, sq="2000", emg=None, sel=None):
            out.append(RawSample(hex=f"{0xf00000 + cyc * 16 + i:06x}", callsign=cs, type=typ, registration=f"SIM-{i}",
                                 lat=float(la), lon=float(lo), alt_baro_ft=float(alt), gs_kt=float(gs),
                                 track_deg=float(trk), vrate_fpm=float(vr), squawk=sq, emergency=emg, sel_alt_ft=sel,
                                 on_ground=False, seen_pos_s=0.5, source=self.name, fetched_at=now))

        pl, po = geo.destination(ap.lat, ap.lon, 0.0, 25.0)                      # head-on pair 25 nm north
        for i, cs, off, trk in ((0, "AIC101", 270.0, 90.0), (1, "IGO202", 90.0, 270.0)):
            sl, so = geo.destination(pl, po, off, 20.0)
            la, lo = geo.dead_reckon(sl, so, trk, 250.0, el)
            add(i, cs, "A20N", la, lo, 12000, 250, trk, 0, sel=12000.0)

        e = ap.runways[0].ends[0]                                                # heavy then medium on final
        for i, cs, typ, d0 in ((2, "UAE303", "B77W", 14.0), (3, "AIC404", "A320", 17.8)):
            d = d0 - 160.0 * el / 3600.0
            if d > 0.5:
                la, lo = geo.destination(e.thr_lat, e.thr_lon, (e.heading_true + 180.0) % 360.0, d)
                add(i, cs, typ, la, lo, ap.elev_ft + d * 318.0, 160, e.heading_true, -850)

        sl, so = geo.destination(ap.lat, ap.lon, 180.0, 8.0)                     # emergency climb-out
        la, lo = geo.dead_reckon(sl, so, 200.0, 220.0, el)
        add(4, "VTI707", "A320", la, lo, 3000 + 1800 * el / 60.0, 220, 200, 1800, sq="7700")
        return out