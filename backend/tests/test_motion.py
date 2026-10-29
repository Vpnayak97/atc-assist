import pytest

from app.core import geo
from app.core.motion import extrapolate, turn_rate_dps
from app.schemas.aircraft import RawSample


def mk(**kw):
    d = dict(hex="a", lat=19.0, lon=72.8, source="x", fetched_at=1000.0, seen_pos_s=0.0,
             gs_kt=360.0, track_deg=90.0, alt_baro_ft=3000.0, vrate_fpm=-600.0)
    d.update(kw)
    return RawSample(**d)


def test_straight_line_distance():
    k = extrapolate(mk(), 1010.0)                       # 360 kt for 10 s = 1 nm
    assert geo.distance_nm(19.0, 72.8, k.lat, k.lon) == pytest.approx(1.0, abs=1e-4)
    assert k.alt_ft == pytest.approx(2900.0)


def test_limit_and_stale():
    k = extrapolate(mk(), 1100.0, limit_s=30.0)
    assert k.extrapolated_s == 30.0 and k.stale


def test_altitude_floor():
    assert extrapolate(mk(alt_baro_ft=50.0, vrate_fpm=-3000.0), 1010.0, floor_ft=39.0).alt_ft == 39.0


def test_turn_rate_and_cap():
    h = [(0, 0, 0, 0, 200, 90.0, 0), (30, 0, 0, 0, 200, 120.0, 0)]
    assert turn_rate_dps(h) == pytest.approx(1.0)
    h2 = [(0, 0, 0, 0, 200, 90.0, 0), (10, 0, 0, 0, 200, 180.0, 0)]
    assert turn_rate_dps(h2) == 3.0
    assert turn_rate_dps([(0, 0, 0, 0, 10, 90.0, 0), (30, 0, 0, 0, 10, 120.0, 0)]) == 0.0   # slow: no turn