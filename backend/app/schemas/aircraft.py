from __future__ import annotations

from enum import Enum, IntEnum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Phase(str, Enum):
    PARKED = "PARKED"
    TAXI = "TAXI"
    LINEUP = "LINEUP"
    TAKEOFF_ROLL = "TAKEOFF_ROLL"
    CLIMB = "CLIMB"
    CRUISE = "CRUISE"
    DESCENT = "DESCENT"
    APPROACH = "APPROACH"
    FINAL = "FINAL"
    LANDING_ROLL = "LANDING_ROLL"
    GO_AROUND = "GO_AROUND"
    HOLDING = "HOLDING"
    UNKNOWN = "UNKNOWN"


class Priority(IntEnum):
    EMERGENCY = 0
    MEDICAL = 1
    STATE = 2
    NORMAL = 3
    LOW = 4


class RawSample(BaseModel):
    """One normalized provider sample. Missing values stay None, never invented."""
    hex: str
    callsign: Optional[str] = None
    type: Optional[str] = None
    registration: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    alt_baro_ft: Optional[float] = None
    alt_geom_ft: Optional[float] = None
    gs_kt: Optional[float] = None
    track_deg: Optional[float] = None
    vrate_fpm: Optional[float] = None
    sel_alt_ft: Optional[float] = None     # pilot-selected altitude (intent), if broadcast
    squawk: Optional[str] = None
    emergency: Optional[str] = None
    on_ground: bool = False
    seen_pos_s: Optional[float] = None     # age of the position when fetched
    source: str
    fetched_at: float                      # epoch s


class Prediction(BaseModel):
    """The contract every model/physics fallback returns (document section 6.3)."""
    kind: Literal["eta", "vertical", "anomaly"]
    value: float
    lo: Optional[float] = None
    hi: Optional[float] = None
    unit: str
    source: Literal["ml", "physics"]
    model_version: Optional[str] = None
    physics_value: Optional[float] = None
    explanation: list[dict] = Field(default_factory=list)
    computed_at: float


class Track(BaseModel):
    hex: str
    callsign: Optional[str] = None
    type: Optional[str] = None
    sample: RawSample                      # last accepted sample
    phase: Phase = Phase.UNKNOWN
    runway: Optional[str] = None           # assigned runway end ident
    dist_nm: Optional[float] = None
    bearing_from_airport: Optional[float] = None
    agl_ft: Optional[float] = None
    quality: float = 1.0                   # 0..1, from source agreement and position age
    position_age_s: float = 0.0
    sources_agreeing: int = 1
    priority: Priority = Priority.NORMAL
    emergency: Optional[str] = None        # "7700", "7600", "7500", "manual", ...
    anomaly: bool = False
    predictions: dict[str, Prediction] = Field(default_factory=dict)
    last_update: float = 0.0