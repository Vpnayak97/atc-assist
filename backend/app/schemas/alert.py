from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    ADVISORY = "ADVISORY"
    CAUTION = "CAUTION"
    WARNING = "WARNING"


class AlertType(str, Enum):
    CONFLICT = "CONFLICT"
    RUNWAY_OCCUPANCY = "RUNWAY_OCCUPANCY"
    GO_AROUND = "GO_AROUND"
    HOLDING = "HOLDING"
    EMERGENCY = "EMERGENCY"
    UNUSUAL_APPROACH = "UNUSUAL_APPROACH"
    DATA_QUALITY = "DATA_QUALITY"
    PROVIDER = "PROVIDER"
    MODEL_FALLBACK = "MODEL_FALLBACK"
    SPACING = "SPACING"

class Alert(BaseModel):
    id: str
    type: AlertType
    severity: Severity
    flights: list[str] = Field(default_factory=list)
    text: str
    created_at: float
    updated_at: float
    acknowledged: bool = False
    cleared: bool = False
    meta: dict = Field(default_factory=dict)
    source_ref: Optional[str] = None       # e.g. rule name or doc passage (RAG later)