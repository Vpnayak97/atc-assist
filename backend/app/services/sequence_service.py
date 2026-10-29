from __future__ import annotations

from app.core import sequencer as sq


class SequenceService:
    def __init__(self, p, airport, geom, sep, audit):
        self.p, self.airport, self.geom, self.sep, self.audit = p, airport, geom, sep, audit
        self.cross = geom.crossing_pairs()
        self.prev: dict[str, float] = {}            # hex -> assigned epoch from the last plan
        self.sig, self.t_solve, self.plan = None, -1e9, None

    def _items(self, rows, now, ga, closed, observed):
        out, horizon = [], self.p.planner_horizon_min * 60.0
        for r in rows:
            if r["gnd"]:
                continue
            hx, is_ga = r["hex"], r["hex"] in ga
            e = (r.get("pred") or {}).get("eta")
            if is_ga:
                eta = max(60.0, ga[hx]["t0"] + self.p.go_around_reinsert_s - now)
            elif e and r["phase"] in ("APPROACH", "FINAL", "DESCENT"):
                eta = float(e["s"])
            else:
                continue
            if eta > horizon:
                continue
            end = (ga[hx].get("rwy") if is_ga else None) or r.get("rwy")
            rid, reassigned = (self.geom.runway_of(end) if end else None), False
            if rid is None or rid in closed:
                reassigned = rid in closed
                end = self.geom.choose_end(r["lat"], r["lon"], r["trk"] or 0.0, observed, exclude=closed) \
                    if r.get("trk") is not None else self.geom.default_end(observed, closed)
                rid = self.geom.runway_of(end) if end else None
            if rid is None or rid in closed:
                continue
            out.append({"hex": hx, "cs": r.get("callsign") or hx.upper(), "type": r.get("type"),
                        "wake": r.get("wake", "M"), "rid": rid, "end": end, "eta": eta, "gs": r.get("gs"),
                        "pri": min(int(r["pri"]), 1) if is_ga else int(r["pri"]),
                        "frozen": (not is_ga) and eta <= self.p.freeze_window_s, "ga": is_ga, "reassigned": reassigned})
        return sorted(out, key=lambda x: x["eta"])[:30]

    def _reason(self, i, items, T, S, delay, pred_i):
        it, bits = items[i], []
        if it["ga"]:
            bits.append("re-sequenced after go-around")
        elif it["pri"] == 0:
            bits.append("emergency priority")
        elif it["pri"] == 1:
            bits.append("priority handling")
        if it["reassigned"]:
            bits.append(f"runway closed, moved to RWY {it['end']}")
        if delay <= 5:
            bits.append("no delay")
        elif pred_i is not None and abs(T[i] - T[pred_i] - S[pred_i][i]) <= 6:
            lead = items[pred_i]
            nm = self.sep.required_nm(lead["type"], it["type"])[0]
            bits.append(f"follows {lead['cs']} ({lead['wake']}>{it['wake']}, {nm:.0f} NM = {S[pred_i][i]} s)")
        else:
            bits.append("spaced behind earlier arrivals or crossing-runway traffic")
        return "; ".join(bits)

    def _solve(self, items, now):
        n = len(items)
        if n == 0:
            self.plan, self.prev = None, {}
            return
        S = [[0 if i == j else sq.pair_sep(a, b, self.sep.required_nm, self.p.rot_s, self.cross, self.p)
              for j, b in enumerate(items)] for i, a in enumerate(items)]
        res = sq.plan(items, S, {h: t - now for h, t in self.prev.items()}, self.p)
        T, base = res["times"], sq.fcfs(items, S)
        delay = lambda tm, i: max(0, tm[i] - items[i]["eta"])
        entries = []
        for pos, i in enumerate(sorted(range(n), key=lambda k: T[k]), 1):
            it = items[i]
            same = [k for k in range(n) if k != i and items[k]["rid"] == it["rid"] and T[k] < T[i]]
            pred_i = max(same, key=lambda k: T[k]) if same else None
            d = delay(T, i)
            entries.append({"hex": it["hex"], "cs": it["cs"], "type": it["type"], "wake": it["wake"], "rwy": it["end"],
                            "rid": it["rid"], "pos": pos, "pri": it["pri"], "frozen": it["frozen"], "ga": it["ga"],
                            "delay": d, "late": d > self.p.max_delay_s, "eta_epoch": now + it["eta"],
                            "assigned_epoch": now + T[i], "reason": self._reason(i, items, T, S, d, pred_i)})
        W = lambda tm: round(sum(sq.weight(items[i]) * delay(tm, i) for i in range(n)) / 10)
        metrics = {"n": n, "total": sum(delay(T, i) for i in range(n)), "fcfs_total": sum(delay(base, i) for i in range(n)),
                   "max": max(delay(T, i) for i in range(n)), "fcfs_max": max(delay(base, i) for i in range(n)),
                   "w": W(T), "fcfs_w": W(base)}
        self.plan = {"generated_at": now, "solver": res["solver"], "solve_ms": res["ms"], "optimal": res["optimal"],
                     "metrics": metrics, "entries": entries}
        self.prev = {e["hex"]: e["assigned_epoch"] for e in entries}
        self.audit.log("sequence_plan", {"solver": res["solver"], "ms": res["ms"], **metrics}, now)

    def update(self, rows, now, ga, closed, observed) -> dict:
        items = self._items(rows, now, ga, closed, observed)
        sig = (tuple(sorted((i["hex"], i["rid"], i["pri"], i["frozen"], i["ga"]) for i in items)), tuple(sorted(closed)))
        if sig != self.sig or now - self.t_solve >= self.p.planner_interval_s:
            self._solve(items, now)
            self.sig, self.t_solve = sig, now
        if not self.plan:
            return {"generated_at": None, "solver": "none", "solve_ms": 0, "optimal": False, "metrics": None,
                    "entries": [], "closed": sorted(closed)}
        ent = [dict(e, eta_in=round(e["eta_epoch"] - now), assigned_in=round(e["assigned_epoch"] - now))
               for e in self.plan["entries"]]
        return {**self.plan, "entries": ent, "closed": sorted(closed)}