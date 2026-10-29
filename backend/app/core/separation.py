from __future__ import annotations

import json
from pathlib import Path

SUPER = {"A388", "A225"}
HEAVY = {"B741", "B742", "B743", "B744", "B748", "B74S", "B772", "B773", "B77L", "B77W", "B762", "B763", "B764",
         "B788", "B789", "B78X", "A306", "A30B", "A310", "A332", "A333", "A338", "A339", "A342", "A343", "A345",
         "A346", "A359", "A35K", "A124", "A400", "IL76", "IL96", "MD11", "DC10", "C5M"}
LIGHT = {"C172", "C182", "C208", "C210", "PA28", "PA32", "PA34", "SR20", "SR22", "BE20", "BE36", "BE58", "DA40",
         "DA42", "TBM7", "TBM8", "TBM9", "PC12", "E50P", "C25A", "C25B", "C510", "C525", "B350", "SF50"}


def wake_category(type_code) -> str:
    """ICAO J/H/M/L. Unknown types default to Medium (and callers flag the pair as 'assumed')."""
    t = (type_code or "").upper()
    return "J" if t in SUPER else "H" if t in HEAVY else "L" if t in LIGHT else "M"


class Separation:
    def __init__(self, data_dir: Path, scheme: str = "ICAO"):
        d = json.loads((Path(data_dir) / "separation_matrix.json").read_text(encoding="utf-8"))
        self.requested = scheme
        self.scheme = scheme if scheme in d else "ICAO"          # RECAT-EU table not loaded yet: falls back
        self.m, self.default = d[self.scheme], float(d.get("default_min_nm", 3.0))

    def required_nm(self, lead_type, follow_type) -> tuple[float, bool]:
        wl, wf = wake_category(lead_type), wake_category(follow_type)
        return float(self.m.get(wl, {}).get(wf, self.default)), not (lead_type and follow_type)