import time

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api")


def health_payload(app) -> dict:
    loop = app.state.fetch
    cyc = loop.last_cycle
    provs = loop.provider_status()
    return {
        "status": "ok" if any(p["ok"] for p in provs) else "degraded",
        "airport": app.state.airport.icao,
        "data_age_s": round(time.time() - cyc["at"], 1) if cyc else None,
        "last_cycle": cyc,
        "providers": provs,
        "models": app.state.registry.status()["models"],
    }


@router.get("/health")
def health(request: Request):
    return health_payload(request.app)