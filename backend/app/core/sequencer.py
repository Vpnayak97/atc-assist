from __future__ import annotations

import math
import time

from ortools.sat.python import cp_model

PRI_W = {0: 1000, 1: 200, 2: 50, 3: 10, 4: 5}


def weight(it) -> int:
    return PRI_W.get(int(it["pri"]), 10)


def pair_sep(a, b, sepnm, rot_s, crossing, p) -> int:
    """Seconds required between landing time of a (leader) and b (follower)."""
    if a["rid"] == b["rid"]:
        req_nm, _ = sepnm(a["type"], b["type"])
        v = min(180.0, max(120.0, b.get("gs") or p.approach_speed_kt))
        return int(math.ceil(max(req_nm / v * 3600.0, rot_s.get(a["wake"], 50.0) + 5.0)))
    return int(p.cross_sep_s) if frozenset((a["rid"], b["rid"])) in crossing else 0


def fcfs(items, S) -> dict:
    t = {}
    for i in sorted(range(len(items)), key=lambda k: (items[k]["eta"], k)):
        lo = math.ceil(items[i]["eta"])
        for k, tk in t.items():
            lo = max(lo, tk + S[k][i])
        t[i] = lo
    return t


def plan(items, S, prev, p) -> dict:
    t0, n = time.perf_counter(), len(items)
    m = cp_model.CpModel()
    lo = [math.ceil(it["eta"]) for it in items]
    T = [m.NewIntVar(lo[i], lo[i] + 1800, f"t{i}") for i in range(n)]
    obj = [weight(items[i]) * (T[i] - lo[i]) for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if S[i][j] == 0 and S[j][i] == 0:
                continue
            b = m.NewBoolVar(f"b{i}_{j}")                       # b: i lands before j
            m.Add(T[j] >= T[i] + S[i][j]).OnlyEnforceIf(b)
            m.Add(T[i] >= T[j] + S[j][i]).OnlyEnforceIf(b.Not())
            a, c = items[i], items[j]
            hi_, hj_ = a["hex"], c["hex"]
            force = None
            if a["frozen"] and c["frozen"]:
                force = prev[hi_] < prev[hj_] if (hi_ in prev and hj_ in prev) else lo[i] <= lo[j]
            elif a["frozen"] and c["pri"] != 0:
                force = True
            elif c["frozen"] and a["pri"] != 0:
                force = False
            if force is not None:
                m.Add(b == (1 if force else 0))
            elif hi_ in prev and hj_ in prev:
                obj.append(p.seq_stability_cost * ((1 - b) if prev[hi_] < prev[hj_] else b))
    m.Minimize(sum(obj))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = p.seq_max_solve_s
    s.parameters.num_workers = 1
    st = s.Solve(m)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        times, solver = {i: int(s.Value(T[i])) for i in range(n)}, "cp_sat"
    else:
        times, solver = fcfs(items, S), "fcfs_fallback"
    return {"times": times, "solver": solver, "optimal": st == cp_model.OPTIMAL,
            "ms": round((time.perf_counter() - t0) * 1000, 1)}