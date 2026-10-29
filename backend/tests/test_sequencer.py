from app.config import Settings
from app.core import sequencer as sq
from app.core.separation import Separation, wake_category

P = Settings()
SEP = Separation(P.data_dir, "ICAO")


def item(hx, eta, rid="09/27", typ="A320", pri=3, frozen=False):
    return dict(hex=hx, cs=hx.upper(), type=typ, wake=wake_category(typ), rid=rid, end="27", eta=float(eta),
                gs=140.0, pri=pri, frozen=frozen, ga=False, reassigned=False)


def mat(items, crossing=frozenset()):
    return [[0 if i == j else sq.pair_sep(a, b, SEP.required_nm, P.rot_s, crossing, P) for j, b in enumerate(items)]
            for i, a in enumerate(items)]


def check_sep(items, S, T):
    order = sorted(range(len(items)), key=lambda i: T[i])
    for a, b in zip(order, order[1:]):
        assert T[b] >= T[a] + S[a][b] or S[a][b] == 0


def test_separation_respected_and_not_worse_than_fcfs():
    items = [item("a", 100), item("b", 110, typ="B77W"), item("c", 120), item("d", 125, typ="C172")]
    S = mat(items)
    res = sq.plan(items, S, {}, P)
    check_sep(items, S, res["times"])
    base = sq.fcfs(items, S)
    w = lambda T: sum(sq.weight(items[i]) * max(0, T[i] - items[i]["eta"]) for i in range(len(items)))
    assert w(res["times"]) <= w(base)


def test_emergency_overtakes():
    items = [item("a", 400), item("b", 410), item("e", 420, pri=0)]
    T = sq.plan(items, mat(items), {}, P)["times"]
    assert T[2] < T[0] and T[2] < T[1]


def test_frozen_not_overtaken():
    items = [item("f", 250, frozen=True), item("n", 240)]
    T = sq.plan(items, mat(items), {}, P)["times"]
    assert T[0] < T[1]


def test_crossing_runways_separated():
    items = [item("a", 100, rid="09/27"), item("b", 105, rid="14/32")]
    S = mat(items, frozenset({frozenset(("09/27", "14/32"))}))
    T = sq.plan(items, S, {}, P)["times"]
    assert abs(T[0] - T[1]) >= P.cross_sep_s
    S2 = mat(items)                                           # without the crossing: independent runways
    assert S2[0][1] == 0