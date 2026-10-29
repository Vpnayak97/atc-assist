from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import flights, health, models_info, ops as ops_api, ws
from app.config import get_airport, get_settings
from app.core.separation import Separation
from app.ml.registry import Registry
from app.providers.adsb_fi import AdsbFi
from app.providers.adsb_lol import AdsbLol
from app.providers.airplanes_live import AirplanesLive
from app.providers.opensky import OpenSky
from app.services.fetch_loop import FetchLoop
from app.services.live_state import LiveState
from app.services.ops_service import OpsService
from app.services.prediction_service import PredictionService
from app.services.tracker import Tracker
from app.services.weather_service import WeatherService

log = logging.getLogger("atc")


def build_providers(s):
    a, b = s.circuit_open_after, s.circuit_probe_after_s
    makers = {
        "adsb_lol": lambda: AdsbLol(a, b),
        "adsb_fi": lambda: AdsbFi(a, b),
        "airplanes_live": lambda: AirplanesLive(a, b),
        "opensky": lambda: OpenSky(
            a, b, s.opensky_client_id, s.opensky_client_secret
        ),
    }
    return [makers[n]() for n in s.provider_order if n in makers]


@asynccontextmanager
async def lifespan(app: FastAPI):
    s, airport = get_settings(), get_airport()

    tracker = Tracker(airport, s)
    fetch = FetchLoop(build_providers(s), tracker, s, airport)

    registry = Registry(s.models_dir)
    predictor = PredictionService(registry, tracker, airport, s)
    fetch.on_cycle = predictor.run

    # Initialize the services used by ws.py and the operations API.
    sep = Separation(s.data_dir, s.separation_scheme)
    ops = OpsService(
        tracker,
        airport,
        s,
        sep,
        s.data_dir / "audit.jsonl",
    )
    weather = WeatherService(airport, s)

    stop = asyncio.Event()

    app.state.airport = airport
    app.state.tracker = tracker
    app.state.fetch = fetch
    app.state.registry = registry
    app.state.predictor = predictor
    app.state.ops = ops
    app.state.weather = weather
    app.state.live = LiveState(tracker, airport, s)
    app.state.hub = ws.Hub()

    tasks = [
        asyncio.create_task(fetch.run()),
        asyncio.create_task(ws.push_loop(app, stop)),
        asyncio.create_task(weather.run(stop)),
    ]

    log.info(
        "ATC-Assist started: %s (separation %s)",
        airport.icao,
        sep.scheme,
    )

    try:
        yield
    finally:
        fetch.stop()
        stop.set()
        await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(
    title="ATC-Assist",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (health.router, flights.router, ws.router, models_info.router, ops_api.router):
    app.include_router(r)


@app.get("/api/airport")
def airport():
    return get_airport().model_dump()
