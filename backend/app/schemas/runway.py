from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class RunwayEnd(BaseModel):
    ident: str                 # e.g. "27"
    thr_lat: float
    thr_lon: float
    heading_true: float
    length_ft: float
    width_ft: float
    opposite: str              # ident of the reciprocal end


class Runway(BaseModel):
    id: str                    # "09/27"
    ends: list[RunwayEnd]      # always two


class Airport(BaseModel):
    icao: str
    lat: float
    lon: float
    elev_ft: float
    runways: list[Runway]

    @classmethod
    def from_raw(cls, icao: str, d: dict) -> "Airport":
        runways: list[Runway] = []
        for r in d.get("runways", []):
            need = ("le_lat", "le_lon", "he_lat", "he_lon", "le_hdg", "he_hdg")
            if any(r.get(k) is None for k in need):
                continue  # incomplete record: skip rather than guess
            length, width = r.get("length_ft") or 0.0, r.get("width_ft") or 0.0
            le = RunwayEnd(ident=r["le"], thr_lat=r["le_lat"], thr_lon=r["le_lon"],
                           heading_true=r["le_hdg"], length_ft=length, width_ft=width, opposite=r["he"])
            he = RunwayEnd(ident=r["he"], thr_lat=r["he_lat"], thr_lon=r["he_lon"],
                           heading_true=r["he_hdg"], length_ft=length, width_ft=width, opposite=r["le"])
            runways.append(Runway(id=f'{r["le"]}/{r["he"]}', ends=[le, he]))
        return cls(icao=icao, lat=d["lat"], lon=d["lon"], elev_ft=d["elev_ft"], runways=runways)

    def end(self, ident: str) -> RunwayEnd:
        for rw in self.runways:
            for e in rw.ends:
                if e.ident == ident:
                    return e
        raise KeyError(ident)


class RunwayStatus(str, Enum):
    FREE = "FREE"
    ARRIVAL_IMMINENT = "ARRIVAL_IMMINENT"
    OCCUPIED = "OCCUPIED"
    CLEARING = "CLEARING"
    CLOSED = "CLOSED"


class ClaimKind(str, Enum):
    ARR = "ARR"
    DEP = "DEP"


class Claim(BaseModel):
    hex: str
    kind: ClaimKind
    start: float               # epoch s
    end: float
    confidence: float = 1.0