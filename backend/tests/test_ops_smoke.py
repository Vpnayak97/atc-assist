from app.config import get_airport, get_settings
from app.core.separation import Separation
from app.services.ops_service import OpsService
from app.services.tracker import Tracker


def row(hx, **kw):
    d = dict(hex=hx, callsign=hx.upper(), type="A320", reg=None, lat=19.1, lon=72.9, x=5.0, y=5.0, alt=4000.0, gs=160.0,
             trk=270.0, vr=-700.0, sq="2000", phase="APPROACH", rwy=None, dist=7.0, brg=45.0, gnd=False, q=1.0, age=1.0,
             stale=False, pri=3, emg=None, src="test", sel=None, wake="M", pred={"eta": {"s": 200, "lo": 180, "hi": 230}})
    d.update(kw)
    return d


def test_ops_update_end_to_end(tmp_path):
    s, ap = get_settings(), get_airport()
    ops = OpsService(Tracker(ap, s), ap, s, Separation(s.data_dir, "ICAO"), tmp_path / "audit.jsonl")
    rows = [row("a1"), row("a2", y=6.0, pred={"eta": {"s": 230}}), row("a3", pri=0, pred={"eta": {"s": 260}}),
            row("c1", alt=35000.0, phase="CRUISE", dist=50.0, pred={})]
    out = ops.update(rows, 1000.0)
    assert {"runways", "rw_conflicts", "sequence", "holds", "go_arounds"} <= set(out)
    seq = out["sequence"]
    assert seq["metrics"]["n"] == 3 and len(seq["entries"]) == 3
    assert seq["entries"][0]["hex"] == "a3"                        # emergency lands first
    rid = seq["entries"][0]["rid"]
    assert ops.rwy.set_closed(rid, True, 1001.0)
    assert ops.update(rows, 1001.0)["sequence"]["closed"] == [rid]