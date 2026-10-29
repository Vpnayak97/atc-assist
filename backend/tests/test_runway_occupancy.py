import numpy as np

from app.core import geo
from app.core import runway_occupancy as ro
from app.core.goaround import detect_goaround, detect_holding
from app.core.runway_geometry import RunwayGeometry
from app.schemas.runway import Airport

CROSS = {"lat": 19.0, "lon": 72.9, "elev_ft": 0.0, "runways": [
    {"le": "09", "he": "27", "le_lat": 19.0, "le_lon": 72.88, "he_lat": 19.0, "he_lon": 72.92, "le_hdg": 90.0,
     "he_hdg": 270.0, "length_ft": 9000.0, "width_ft": 150.0},
    {"le": "18", "he": "36", "le_lat": 19.02, "le_lon": 72.9, "he_lat": 18.98, "he_lon": 72.9, "le_hdg": 180.0,
     "he_hdg": 360.0, "length_ft": 9000.0, "width_ft": 150.0}]}
PAR = {**CROSS, "runways": [CROSS["runways"][0], {**CROSS["runways"][0], "le": "09R", "he": "27L",
                                                     "le_lat": 19.02, "he_lat": 19.02}]}


def row(hx, eta, rwy="27", wake="M"):
    return dict(hex=hx, callsign=hx.upper(), gnd=False, rwy=rwy, phase="FINAL", wake=wake, lat=19.0, lon=73.0,
                trk=270.0, gs=140.0, pred={"eta": {"s": eta}})


def test_crossing_detection():
    assert RunwayGeometry(Airport.from_raw("T", CROSS)).crossing_pairs() == {frozenset({"09/27", "18/36"})}
    assert RunwayGeometry(Airport.from_raw("T", PAR)).crossing_pairs() == set()


def test_overlapping_arrivals_flagged():
    g = RunwayGeometry(Airport.from_raw("T", CROSS))
    claims = ro.build_claims([row("a", 100), row("b", 120)], g, {"M": 50.0}, {})
    c = ro.find_conflicts(claims, g.crossing_pairs())
    assert len(c) == 1 and c[0]["sev"] == "CAUTION" and c[0]["overlap"] == 40
    far = ro.build_claims([row("a", 100), row("b", 200)], g, {"M": 50.0}, {})
    assert ro.find_conflicts(far, g.crossing_pairs()) == []
    assert ro.status_for("09/27", far["09/27"], set()) == "FREE"
    assert ro.status_for("09/27", far["09/27"], {"09/27"}) == "CLOSED"


def hist(dists, agls, vr):
    out = []
    for k, (d, a) in enumerate(zip(dists, agls)):
        la, lo = geo.destination(19.0, 72.9, 90.0, d)
        out.append((1000.0 + 30 * k, float(la), float(lo), a, 150.0, 270.0, vr[k]))
    return out


def test_goaround_vs_departure():
    ga = hist([10, 8, 6, 4, 2.5, 3.5, 5.5], [3000, 2400, 1800, 1200, 600, 1300, 2000], [-700] * 4 + [-500, 1500, 1500])
    r = detect_goaround(ga, 19.0, 72.9, 0.0)
    assert r is not None and r["climb"] >= 500
    dep = hist([0.5, 2, 4, 6, 9], [100, 700, 1500, 2200, 2800], [1500] * 5)
    assert detect_goaround(dep, 19.0, 72.9, 0.0) is None


def test_holding():
    h = [(1000.0 + 40 * k, 19.0 + 0.001 * (k % 2), 72.9, 6000.0, 220.0, (45.0 * k) % 360, 0.0) for k in range(10)]
    assert detect_holding(h) is not None
    straight = [(1000.0 + 40 * k, 19.0, 72.9 + 0.05 * k, 6000.0, 220.0, 90.0, 0.0) for k in range(10)]
    assert detect_holding(straight) is None