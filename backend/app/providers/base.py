from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from app.schemas.aircraft import RawSample

log = logging.getLogger("atc.providers")


# ---------------------------------------------------------------- helpers
def _num(x: Any) -> Optional[float]:
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    return None


def parse_readsb(ac_list: list[dict], source: str, fetched_at: float) -> list[RawSample]:
    """Map readsb-style aircraft records (adsb.lol, airplanes.live) to RawSample.
    Missing values stay None. Records without hex or position are skipped."""
    out: list[RawSample] = []
    for a in ac_list:
        hx = str(a.get("hex") or "").strip().lower()
        if not hx or hx.startswith("~"):          # '~' = non-ICAO address (e.g. TIS-B)
            continue
        lat, lon = _num(a.get("lat")), _num(a.get("lon"))
        if lat is None or lon is None:
            continue
        alt_raw = a.get("alt_baro")
        on_ground = alt_raw == "ground"
        alt_baro = None if on_ground else _num(alt_raw)
        vrate = _num(a.get("baro_rate"))
        if vrate is None:
            vrate = _num(a.get("geom_rate"))
        emerg = a.get("emergency")
        emerg = None if (emerg in (None, "", "none")) else str(emerg)
        sq = a.get("squawk")
        out.append(RawSample(
            hex=hx,
            callsign=(str(a["flight"]).strip() or None) if a.get("flight") else None,
            type=(str(a["t"]).strip().upper() or None) if a.get("t") else None,
            registration=(str(a["r"]).strip() or None) if a.get("r") else None,
            lat=lat, lon=lon,
            alt_baro_ft=alt_baro, alt_geom_ft=_num(a.get("alt_geom")),
            gs_kt=_num(a.get("gs")), track_deg=_num(a.get("track")), vrate_fpm=vrate,
            squawk=str(sq) if sq else None, emergency=emerg, on_ground=on_ground,
            seen_pos_s=_num(a.get("seen_pos")) if a.get("seen_pos") is not None else _num(a.get("seen")),
            sel_alt_ft=(_num(a.get("nav_altitude_mcp")) if a.get("nav_altitude_mcp") is not None
                        else _num(a.get("nav_altitude_fms"))),
            source=source, fetched_at=fetched_at,
        ))
    return out


# ---------------------------------------------------------------- resilience
class CircuitBreaker:
    """closed -> open after N consecutive failures -> half-open probe after a pause."""

    def __init__(self, open_after: int = 3, probe_after_s: float = 60.0):
        self.open_after, self.probe_after_s = open_after, probe_after_s
        self.failures = 0
        self.opened_at: Optional[float] = None

    def state(self, now: float) -> str:
        if self.opened_at is None:
            return "closed"
        return "half_open" if now - self.opened_at >= self.probe_after_s else "open"

    def allow(self, now: float) -> bool:
        return self.state(now) != "open"

    def success(self) -> None:
        self.failures, self.opened_at = 0, None

    def failure(self, now: float) -> None:
        self.failures += 1
        if self.failures >= self.open_after:
            self.opened_at = now


@dataclass
class ProviderStatus:
    name: str
    state: str = "closed"
    ok: bool = False
    last_success: Optional[float] = None
    last_error: Optional[str] = None
    latency_ms: Optional[float] = None
    n_samples: int = 0


class Provider(ABC):
    name: str = "base"
    min_interval_s: float = 1.0
    poll_interval_s: float = 0.0     # 0 = every cycle; OpenSky overrides this

    def __init__(self, open_after: int = 3, probe_after_s: float = 60.0):
        self.breaker = CircuitBreaker(open_after, probe_after_s)
        self.status = ProviderStatus(self.name)
        self._last_call = -1e9       # was 0.0
        self._cooldown_until = 0.0
        self._backoff_s = 30.0

    @abstractmethod
    async def _fetch(self, client: httpx.AsyncClient, lat: float, lon: float, radius_nm: float) -> list[RawSample]: ...

    async def fetch(self, client: httpx.AsyncClient, lat: float, lon: float, radius_nm: float) -> list[RawSample]:
        """Never raises. Returns [] on failure and records why in self.status."""
        import asyncio
        now = time.time()
        self.status.state = self.breaker.state(now)
        if not self.breaker.allow(now):
            self.status.ok, self.status.last_error = False, "circuit open"
            return []
        if now < self._cooldown_until:
            self.status.ok, self.status.last_error = False, f"rate-limit cooldown {self._cooldown_until - now:.0f}s"
            return []
        if self.poll_interval_s and (time.monotonic() - self._last_call) < self.poll_interval_s:
            return []                 # not due yet; status left unchanged
        wait = self.min_interval_s - (time.monotonic() - self._last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_call = time.monotonic()
        t0 = time.perf_counter()
        try:
            samples = await self._fetch(client, lat, lon, min(radius_nm, 250.0))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                self._cooldown_until = time.time() + self._backoff_s
                self._backoff_s = min(self._backoff_s * 2, 300.0)
            self._fail(f"HTTP {e.response.status_code}")
            return []
        except (httpx.HTTPError, ValueError) as e:
            self._fail(f"{type(e).__name__}: {e}")
            return []
        self.breaker.success()
        self._backoff_s = 30.0
        self.status = ProviderStatus(self.name, state="closed", ok=True, last_success=time.time(),
                                     latency_ms=(time.perf_counter() - t0) * 1000, n_samples=len(samples))
        return samples

    def _fail(self, msg: str) -> None:
        self.breaker.failure(time.time())
        log.warning("provider %s failed: %s", self.name, msg)
        self.status.ok, self.status.last_error = False, msg
        self.status.state = self.breaker.state(time.time())


class ReadsbProvider(Provider):
    base_url: str = ""

    async def _fetch(self, client, lat, lon, radius_nm):
        url = f"{self.base_url}/point/{lat:.4f}/{lon:.4f}/{radius_nm:.0f}"
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return parse_readsb(data.get("ac") or [], self.name, time.time())