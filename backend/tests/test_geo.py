import numpy as np
import pytest

from app.core import geo


def test_one_degree_latitude_is_about_60nm():
    assert geo.distance_nm(0, 0, 1, 0) == pytest.approx(60.04, abs=0.05)


def test_distance_zero_and_symmetry():
    assert geo.distance_nm(19.0, 72.8, 19.0, 72.8) == pytest.approx(0.0, abs=1e-9)
    a = geo.distance_nm(19.0, 72.8, 28.5, 77.1)
    b = geo.distance_nm(28.5, 77.1, 19.0, 72.8)
    assert a == pytest.approx(b)


def test_bearing_cardinals():
    assert geo.bearing_deg(0, 0, 1, 0) == pytest.approx(0.0, abs=1e-6)
    assert geo.bearing_deg(0, 0, 0, 1) == pytest.approx(90.0, abs=1e-6)
    assert geo.bearing_deg(0, 0, -1, 0) == pytest.approx(180.0, abs=1e-6)
    assert geo.bearing_deg(0, 0, 0, -1) == pytest.approx(270.0, abs=1e-6)


def test_destination_round_trip():
    lat, lon = 19.0887, 72.8679
    for brg in (0, 45, 133, 271, 359):
        lat2, lon2 = geo.destination(lat, lon, brg, 25.0)
        assert geo.distance_nm(lat, lon, lat2, lon2) == pytest.approx(25.0, abs=1e-6)
        assert geo.bearing_deg(lat, lon, lat2, lon2) == pytest.approx(brg, abs=1e-4)


def test_dead_reckon_120kt_for_30s_is_1nm():
    lat2, lon2 = geo.dead_reckon(19.0, 72.8, 90.0, 120.0, 30.0)
    assert geo.distance_nm(19.0, 72.8, lat2, lon2) == pytest.approx(1.0, abs=1e-6)


def test_angle_diff_wraps():
    assert geo.angle_diff(350, 10) == pytest.approx(-20.0)
    assert geo.angle_diff(10, 350) == pytest.approx(20.0)


def test_xy_round_trip():
    lat0, lon0 = 19.0887, 72.8679
    x, y = geo.to_xy_nm(19.3, 73.1, lat0, lon0)
    lat, lon = geo.from_xy_nm(x, y, lat0, lon0)
    assert lat == pytest.approx(19.3, abs=1e-6)
    assert lon == pytest.approx(73.1, abs=1e-6)


def test_runway_frame_on_centreline():
    thr_lat, thr_lon, hdg = 19.0, 72.8, 270.0
    # point 5 nm before the threshold, on the extended centreline (east of it, heading west)
    lat, lon = geo.destination(thr_lat, thr_lon, 90.0, 5.0)
    along, cross = geo.runway_frame(lat, lon, thr_lat, thr_lon, hdg)
    assert along == pytest.approx(-5.0, abs=1e-3)
    assert cross == pytest.approx(0.0, abs=1e-3)


def test_runway_frame_right_of_track():
    thr_lat, thr_lon, hdg = 19.0, 72.8, 270.0
    # heading west, right-hand side is north
    lat, lon = geo.destination(thr_lat, thr_lon, 0.0, 1.0)
    _, cross = geo.runway_frame(lat, lon, thr_lat, thr_lon, hdg)
    assert cross == pytest.approx(1.0, abs=1e-3)


def test_vectorized():
    d = geo.distance_nm(np.array([0.0, 1.0]), np.array([0.0, 0.0]), 0.0, 0.0)
    assert d.shape == (2,)