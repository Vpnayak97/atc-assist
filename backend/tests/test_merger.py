from app.core import geo
from app.providers.base import parse_readsb
from app.providers.merger import merge

ORDER = ["adsb_lol", "airplanes_live"]


def mk(hx="abc123", lat=19.0, lon=72.8, source="adsb_lol", age=1.0, fetched=1000.0, **kw):
    from app.schemas.aircraft import RawSample
    return RawSample(hex=hx, lat=lat, lon=lon, source=source, seen_pos_s=age, fetched_at=fetched,
                     gs_kt=200.0, alt_baro_ft=3000.0, **kw)


def test_picks_freshest_and_counts_agreement():
    out = merge({"adsb_lol": [mk(age=10)], "airplanes_live": [mk(source="airplanes_live", age=2)]}, {}, ORDER)
    assert len(out) == 1 and out[0].sample.source == "airplanes_live"
    assert out[0].sources_agreeing == 2


def test_fills_missing_identity_from_other_source():
    a = mk(age=1)                                                    # freshest, no callsign
    b = mk(source="airplanes_live", age=5, callsign="AIC101", type="A320")
    out = merge({"adsb_lol": [a], "airplanes_live": [b]}, {}, ORDER)
    assert out[0].sample.callsign == "AIC101" and out[0].sample.type == "A320"


def test_rejects_position_jump():
    prev = mk(fetched=1000.0, age=0)
    lat2, lon2 = geo.destination(19.0, 72.8, 90, 60.0)               # 60 nm in 30 s = 7200 kt
    new = mk(lat=float(lat2), lon=float(lon2), fetched=1030.0, age=0)
    assert merge({"adsb_lol": [new]}, {"abc123": prev}, ORDER) == []


def test_accepts_normal_motion():
    prev = mk(fetched=1000.0, age=0)
    lat2, lon2 = geo.dead_reckon(19.0, 72.8, 90, 200, 30)
    new = mk(lat=float(lat2), lon=float(lon2), fetched=1030.0, age=0)
    assert len(merge({"adsb_lol": [new]}, {"abc123": prev}, ORDER)) == 1


def test_drops_older_than_previous():
    prev = mk(fetched=1030.0, age=0)
    old = mk(fetched=1030.0, age=20)                                  # position 20 s older than prev
    assert merge({"adsb_lol": [old]}, {"abc123": prev}, ORDER) == []


def test_rejects_implausible_speed():
    bad = mk()
    bad.gs_kt = 1500.0
    assert merge({"adsb_lol": [bad]}, {}, ORDER) == []


def test_quality_lower_for_single_source():
    one = merge({"adsb_lol": [mk(age=1)]}, {}, ORDER)[0].quality
    two = merge({"adsb_lol": [mk(age=1)], "airplanes_live": [mk(source="airplanes_live", age=1)]}, {}, ORDER)[0].quality
    assert two > one
def test_drops_samples_older_than_cap():
    assert merge({"adsb_lol": [mk(age=90)]}, {}, ORDER) == []

def test_parse_readsb_handles_ground_and_junk():
    ac = [
        {"hex": "AAA111", "flight": "IGO123 ", "t": "a320", "lat": 19.1, "lon": 72.9, "alt_baro": "ground",
         "gs": 12.0, "emergency": "none", "squawk": "2000", "seen_pos": 0.4},
        {"hex": "~bbb222", "lat": 19.0, "lon": 72.8},                 # non-ICAO
        {"hex": "ccc333"},                                            # no position
        {"hex": "ddd444", "lat": 19.2, "lon": 72.7, "alt_baro": 2500, "baro_rate": -700, "emergency": "lifeguard"},
    ]
    out = parse_readsb(ac, "adsb_lol", 1000.0)
    assert [s.hex for s in out] == ["aaa111", "ddd444"]
    assert out[0].on_ground and out[0].alt_baro_ft is None and out[0].callsign == "IGO123"
    assert out[0].type == "A320" and out[0].emergency is None
    assert out[1].vrate_fpm == -700 and out[1].emergency == "lifeguard"