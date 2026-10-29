from __future__ import annotations

import asyncio
import logging
import math
import re

import httpx

log = logging.getLogger("atc.wx")
URL = "https://aviationweather.gov/api/data/metar?ids={icao}&format=json"
WIND = re.compile(r"\b(VRB|\d{3})(\d{2,3})(?:G(\d{2,3}))?(KT|MPS)\b")


def parse_metar(obj: dict) -> dict:
    raw = obj.get("rawOb") or obj.get("raw_text") or ""
    out = {"raw": raw, "wdir": None, "wspd": None, "wgst": None, "vrb": False, "qnh": None, "vis": None, "temp": None}
    m = WIND.search(raw)
    if m:
        k = 1.944 if m.group(4) == "MPS" else 1.0
        out["vrb"] = m.group(1) == "VRB"
        out["wdir"] = None if out["vrb"] else int(m.group(1))
        out["wspd"] = round(int(m.group(2)) * k)
        out["wgst"] = round(int(m.group(3)) * k) if m.group(3) else None
    q = re.search(r"\bQ(\d{4})\b", raw)
    out["qnh"] = int(q.group(1)) if q else None
    out["vis"] = "CAVOK" if "CAVOK" in raw else (re.search(r"\b(\d{4})\b", raw[m.end():] if m else raw) or [None, None])[1]
    t = re.search(r"\b(M?\d{2})/(M?\d{2})\b", raw)
    out["temp"] = t.group(1).replace("M", "-") if t else None
    return out


def wind_components(hdg: float, wdir: float, wspd: float) -> tuple[float, float]:
    d = math.radians(wdir - hdg)
    return wspd * math.cos(d), wspd * math.sin(d)          # headwind (+) / tailwind (-), crosswind (+ from right)


class WeatherService:
    def __init__(self, airport, settings):
        self.airport, self.s = airport, settings
        self.data, self.error = None, None

    async def run(self, stop: asyncio.Event) -> None:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "ATC-Assist/0.1 (student project)"}) as c:
            while not stop.is_set():
                try:
                    r = await c.get(URL.format(icao=self.airport.icao))
                    r.raise_for_status()
                    j = r.json()
                    if j:
                        self.data, self.error = parse_metar(j[0]), None
                    else:
                        self.error = "no METAR returned"
                except Exception as e:
                    self.error = f"{type(e).__name__}: {e}"
                    log.warning("METAR fetch failed: %s", self.error)
                try:
                    await asyncio.wait_for(stop.wait(), timeout=self.s.metar_interval_s)
                except asyncio.TimeoutError:
                    pass

    def payload(self, finals: dict) -> dict:
        d, rws, best = self.data, [], None
        if d and d["wdir"] is not None and d["wspd"] is not None:
            wd = (d["wdir"] + self.s.magnetic_variation_deg) % 360
            for rw in self.airport.runways:
                for e in rw.ends:
                    h, x = wind_components(e.heading_true, wd, d["wspd"])
                    rws.append({"ident": e.ident, "head": round(h), "cross": round(x)})
            if d["wspd"] >= 3 and rws:
                best = max(rws, key=lambda r: r["head"])["ident"]
        return {"ok": d is not None, "error": self.error, "metar": d, "runways": rws, "best": best, "observed": finals}