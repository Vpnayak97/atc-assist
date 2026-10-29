from app.config import Settings
from app.core.conflict import detect
from app.core.resolution import resolve

P = Settings()


def ac(hx, x, y, trk, alt=10000.0, gs=240.0, vr=0.0, sel=None, **kw):
    d = dict(hex=hx, callsign=hx.upper(), type="A320", reg=None, x=x, y=y, trk=trk, alt=alt, gs=gs, vr=vr, sel=sel,
             gnd=False, phase="CRUISE", dist=40.0, age=1.0, pri=3, lat=0.0, lon=0.0)
    d.update(kw)
    return d


def test_head_on_detected():
    c = detect([ac("a", -10, 0, 90), ac("b", 10, 0, 270)], P)
    assert len(c) == 1 and c[0]["sev"] == "ADVISORY" and 100 <= c[0]["t_viol"] <= 125


def test_vertical_and_diverging_are_clear():
    assert detect([ac("a", -10, 0, 90, alt=10000), ac("b", 10, 0, 270, alt=12000)], P) == []
    assert detect([ac("a", -10, 0, 270), ac("b", 10, 0, 90)], P) == []


def test_intent_altitude_prevents_false_alert():
    a, b = ac("a", -10, 0, 90, alt=8500, vr=1500), ac("b", 10, 0, 270, alt=10000)
    assert len(detect([a, b], P)) == 1                      # unknown intent: keeps climbing into the other aircraft
    assert detect([dict(a, sel=9000.0), b], P) == []        # selected altitude 9000: levels off 1000 ft below


def test_ground_and_stale_ignored():
    assert detect([ac("a", -10, 0, 90, gnd=True), ac("b", 10, 0, 270)], P) == []
    assert detect([ac("a", -10, 0, 90, age=60.0), ac("b", 10, 0, 270)], P) == []


def test_loss_of_separation_now_is_warning():
    c = detect([ac("a", -2, 0, 90, gs=100), ac("b", 2, 0, 270, gs=100)], P)
    assert c[0]["sev"] == "WARNING" and c[0]["los"]


def test_resolution_options():
    a, b = ac("a", -10, 0, 90, callsign="AIC101"), ac("b", 10, 0, 270, callsign="IGO612C")
    rows, by = [a, b], {"a": a, "b": b}
    opts = resolve(detect(rows, P)[0], by, rows, P, 39.0, 4000.0)
    assert opts and opts[0]["resolved"] and opts[0]["margin"] >= P.resolution_margin
    assert opts[0]["text"].startswith(("Air India", "IndiGo")) and "Traffic" in opts[0]["text"]


def test_no_vectoring_aircraft_on_final():
    a, b = ac("a", -10, 0, 90, phase="FINAL"), ac("b", 10, 0, 270, phase="FINAL")
    assert resolve(detect([a, b], P)[0], {"a": a, "b": b}, [a, b], P, 39.0, 4000.0) == []