from __future__ import annotations

from typing import Iterable, Optional

from app.schemas.aircraft import Phase


def candidate_phase(*, on_ground: bool, gs_kt, agl_ft, vrate_fpm, dist_nm: float, rel_brg,
                    assigned_runway: Optional[str], on_runway: Optional[str], prev: Phase) -> Phase:
    gs, vr = gs_kt or 0.0, vrate_fpm or 0.0
    if on_ground:
        if on_runway:
            if gs >= 40:
                return (Phase.LANDING_ROLL if prev in (Phase.FINAL, Phase.APPROACH, Phase.LANDING_ROLL, Phase.GO_AROUND)
                        else Phase.TAKEOFF_ROLL)
            return Phase.LINEUP
        return Phase.PARKED if gs < 2 else Phase.TAXI
    if agl_ft is None:
        return Phase.UNKNOWN
    if assigned_runway and dist_nm <= 12 and agl_ft < 3500 and vr < 300:
        return Phase.FINAL
    if dist_nm <= 25 and agl_ft < 6000 and vr <= 300 and rel_brg is not None and abs(rel_brg) < 75:
        return Phase.APPROACH
    if vr > 300:
        return Phase.CLIMB
    if vr < -300:
        return Phase.DESCENT
    return Phase.CRUISE


class PhaseMachine:
    """Hysteresis: a new phase must be the candidate for `confirm` consecutive ticks.
    Applied per 1 Hz tick (not per fetch) so landing/takeoff transitions are not delayed by a minute."""

    def __init__(self, confirm: int = 3):
        self.confirm = confirm
        self.state: dict[str, list] = {}      # hex -> [phase, pending, count]

    def update(self, hx: str, cand: Phase) -> Phase:
        st = self.state.get(hx)
        if st is None:
            self.state[hx] = [cand, cand, 0]
            return cand
        if cand == st[0]:
            st[1], st[2] = cand, 0
            return st[0]
        if cand == st[1]:
            st[2] += 1
        else:
            st[1], st[2] = cand, 1
        if st[2] >= self.confirm:
            st[0], st[2] = cand, 0
        return st[0]

    def forget_except(self, keep: Iterable[str]) -> None:
        keep = set(keep)
        for hx in [h for h in self.state if h not in keep]:
            del self.state[hx]