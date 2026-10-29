from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SequenceEntry(BaseModel):
    hex: str
    callsign: Optional[str] = None
    runway: str
    position: int
    eta_s: float                           # unconstrained ETA from now
    assigned_time: float                   # epoch s
    advised_delay_s: float
    frozen: bool = False
    priority: int = 3
    reason: str = ""


class Sequence(BaseModel):
    generated_at: float
    solver: Literal["cp_sat", "fcfs_fallback"]
    solve_time_ms: float
    entries: list[SequenceEntry] = Field(default_factory=list)