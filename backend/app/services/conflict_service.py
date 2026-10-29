from __future__ import annotations

from app.core.conflict import detect
from app.core.phraseology import short_cs, spoken_cs
from app.core.resolution import resolve
from app.schemas.alert import AlertType, Severity


class ConflictService:
    def __init__(self, p, airport, audit, alerts):
        self.p, self.airport, self.audit, self.alerts = p, airport, audit, alerts
        self.state: dict[str, dict] = {}
        self.pair_adv: dict[str, list] = {}
        self.rejected: dict[str, float] = {}
        self.issued: list[dict] = []
        self._last_regen = 0.0

    # ---- controller actions ------------------------------------------------
    def _find(self, adv_id):
        for k, lst in self.pair_adv.items():
            for a in lst:
                if a["id"] == adv_id:
                    return k, a
        return None, None

    def approve(self, adv_id: str, now: float):
        k, a = self._find(adv_id)
        if a is None or a["status"] != "PROPOSED":
            return None
        a["status"], a["issued_at"] = "APPROVED", now
        self.pair_adv[k] = [a]
        if k in self.state:
            self.state[k]["issued_at"] = now
        rec = {"id": a["id"], "text": a["text"], "short": a["short"], "at": now, "hex": a["hex"], "cs": a["cs"]}
        self.issued.insert(0, rec)
        del self.issued[30:]
        self.audit.log("instruction_approved", {**rec, "simulated": True}, now)
        return rec

    def reject(self, adv_id: str, now: float) -> bool:
        k, a = self._find(adv_id)
        if a is None:
            return False
        self.rejected[adv_id] = now
        self.pair_adv[k] = [x for x in self.pair_adv[k] if x["id"] != adv_id]
        self.audit.log("instruction_rejected", {"id": adv_id, "text": a["text"]}, now)
        return True

    # ---- 1 Hz update ---------------------------------------------------------
    def update(self, rows: list[dict], now: float):
        p = self.p
        by_hex = {r["hex"]: r for r in rows}
        found = {c["key"]: c for c in detect(rows, p)}
        for k, c in found.items():
            st = self.state.setdefault(k, {"hits": 0, "miss": 0, "confirmed": False, "issued_at": None})
            st["hits"] += 1
            st["miss"], st["last"] = 0, c
            st["confirmed"] = st["confirmed"] or st["hits"] >= p.conflict_confirm_ticks
        for k in list(self.state):
            if k in found:
                continue
            st = self.state[k]
            if not st["confirmed"]:
                del self.state[k]
                continue
            st["miss"] += 1
            if st["miss"] >= p.conflict_clear_ticks:
                del self.state[k]
                self.pair_adv.pop(k, None)

        regen = now - self._last_regen >= p.advisory_interval_s
        conflicts = []
        for k, st in self.state.items():
            if not st["confirmed"] or st["miss"] > 0:
                continue
            c = st["last"]
            a, b = by_hex.get(c["a"]), by_hex.get(c["b"])
            if a is None or b is None:
                continue
            issued = st["issued_at"] is not None and now - st["issued_at"] < p.advisory_valid_s
            if st["issued_at"] is not None and not issued:           # no change observed: propose again
                st["issued_at"] = None
                self.pair_adv.pop(k, None)
            if not issued and (regen or k not in self.pair_adv):
                opts = resolve(c, by_hex, rows, p, self.airport.elev_ft, p.transition_altitude_ft)
                self.pair_adv[k] = [dict(o, status="PROPOSED", issued_at=None) for o in opts
                                    if now - self.rejected.get(o["id"], -1e9) >= p.advisory_valid_s]
            ca, cb = short_cs(a), short_cs(b)
            t = int(round(c["t_viol"] / 5.0) * 5)
            text = (f"{ca} / {cb}: LOSS OF SEPARATION" if c["los"]
                    else f"{ca} / {cb}: conflict in {t} s, {c['h_min']:.1f} NM / {c['v_min']:.0f} FT")
            sa, sb = spoken_cs(a), spoken_cs(b)
            speech = f"Traffic alert. {sa} and {sb}. " + ("Loss of separation." if c["los"] else f"Conflict in {t} seconds.")
            self.alerts.raise_(f"CONF:{k}", AlertType.CONFLICT, Severity(c["sev"]), [c["a"], c["b"]], text, now,
                               {"speech": speech, "clear_speech": f"{sa} and {sb}, clear of conflict.", "issued": issued})
            conflicts.append({k2: c[k2] for k2 in ("key", "a", "b", "sev", "t_viol", "t_min", "h_min", "v_min", "los",
                                                   "hreq", "vreq", "ax", "ay", "bx", "by")}
                             | {"ca": ca, "cb": cb, "issued": issued})
        if regen:
            self._last_regen = now
        advisories = [a for k, lst in self.pair_adv.items() if k in self.state for a in lst]
        return conflicts, advisories