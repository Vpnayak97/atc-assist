from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import httpx

from app.config import Settings
from app.providers.base import Provider
from app.providers.merger import merge
from app.schemas.runway import Airport
from app.services.tracker import Tracker

log = logging.getLogger("atc.fetch")


class FetchLoop:
    def __init__(self, providers: list[Provider], tracker: Tracker, settings: Settings, airport: Airport):
        self.providers, self.tracker, self.settings, self.airport = providers, tracker, settings, airport
        self.last_cycle: dict = {}
        self._stop = asyncio.Event()
        self.on_cycle = None

    async def fetch_once(self, client: httpx.AsyncClient) -> dict:
        t0 = time.time()
        a, s = self.airport, self.settings
        results = await asyncio.gather(*[p.fetch(client, a.lat, a.lon, s.query_radius_nm) for p in self.providers])
        batches = {p.name: r for p, r in zip(self.providers, results)}
        merged = merge(batches, self.tracker.last_samples(), [p.name for p in self.providers],
                       s.max_plausible_gs_kt, s.max_position_jump_kt)
        now = time.time()
        new = self.tracker.update(merged, now)
        dropped = self.tracker.prune(now)

        if self.on_cycle:
            try:
                self.on_cycle(now)
            except Exception:
                log.exception("prediction cycle failed")

        self.last_cycle = {
            "at": now, "duration_ms": round((now - t0) * 1000), "tracks": len(self.tracker.tracks),
            "new": new, "dropped": len(dropped), "merged": len(merged),
            "per_provider": {k: len(v) for k, v in batches.items()},
        }
        log.info("cycle %s", self.last_cycle)
        return self.last_cycle

    async def run(self) -> None:
        interval = max(5.0, self.settings.fetch_interval_s)
        async with httpx.AsyncClient(timeout=self.settings.http_timeout_s,
                                     headers={"User-Agent": "ATC-Assist/0.1 (student project)"}) as client:
            while not self._stop.is_set():
                started = time.monotonic()
                try:
                    await self.fetch_once(client)
                except Exception:                      # one bad cycle must not kill the loop
                    log.exception("fetch cycle failed")
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=max(0.0, interval - (time.monotonic() - started)))
                except asyncio.TimeoutError:
                    pass

    def stop(self) -> None:
        self._stop.set()

    def provider_status(self) -> list[dict]:
        out = []
        for p in self.providers:
            p.status.state = p.breaker.state(time.time())
            out.append(p.status.__dict__.copy())
        return out