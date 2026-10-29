"""Pure fusion logic: de-duplicate by hex, pick the best sample, fill gaps, score quality."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.core import geo
from app.schemas.aircraft import RawSample

FILL_FIELDS = ("callsign", "type", "registration", "squawk", "emergency", "alt_geom_ft", "sel_alt_ft")


@dataclass
class Merged:
    sample: RawSample
    sources_agreeing: int
    position_age_s: float
    quality: float
    providers: list[str] = field(default_factory=list)


def pos_time(s: RawSample) -> float:
    return s.fetched_at - (s.seen_pos_s or 0.0)


def _valid(s: RawSample, max_gs: float) -> bool:
    if s.lat is None or s.lon is None or not (-90 <= s.lat <= 90) or not (-180 <= s.lon <= 180):
        return False
    if s.gs_kt is not None and not (0 <= s.gs_kt <= max_gs):
        return False
    if s.alt_baro_ft is not None and s.alt_baro_ft < -1500:
        return False
    return True


def _jumps(s: RawSample, prev: RawSample, max_kt: float) -> bool:
    dt = max(pos_time(s) - pos_time(prev), 1.0)
    if dt > 120:               # too long ago to judge
        return False
    d = float(geo.distance_nm(prev.lat, prev.lon, s.lat, s.lon))
    return d / (dt / 3600.0) > max_kt


def merge(batches: dict[str, list[RawSample]], prev: dict[str, RawSample],
          provider_order: list[str], max_gs_kt: float = 700.0,
          max_jump_kt: float = 800.0, agree_nm: float = 1.0,
          max_age_s: float = 60.0) -> list[Merged]:
    by_hex: dict[str, list[RawSample]] = {}
    for samples in batches.values():
        for s in samples:
            if _valid(s, max_gs_kt) and (s.seen_pos_s is None or s.seen_pos_s <= max_age_s):
                by_hex.setdefault(s.hex, []).append(s)

    rank = {p: i for i, p in enumerate(provider_order)}
    out: list[Merged] = []
    for hx, group in by_hex.items():
        p = prev.get(hx)
        if p is not None:
            group = [s for s in group
                     if pos_time(s) >= pos_time(p) - 0.5 and not _jumps(s, p, max_jump_kt)]
        if not group:
            continue
        group.sort(key=lambda s: ((s.seen_pos_s if s.seen_pos_s is not None else 99.0), rank.get(s.source, 99)))
        best = group[0]
        fills = {}
        for f in FILL_FIELDS:
            if getattr(best, f) is None:
                for o in group[1:]:
                    if getattr(o, f) is not None:
                        fills[f] = getattr(o, f)
                        break
        if fills:
            best = best.model_copy(update=fills)

        agree = 1 + sum(1 for o in group[1:]
                        if float(geo.distance_nm(best.lat, best.lon, o.lat, o.lon)) <= agree_nm)
        age = max(0.0, best.seen_pos_s if best.seen_pos_s is not None else 0.0)
        quality = max(0.0, 1.0 - age / 20.0) * (1.0 if agree >= 2 else 0.85)
        out.append(Merged(best, agree, age, round(quality, 3), [s.source for s in group]))
    return out