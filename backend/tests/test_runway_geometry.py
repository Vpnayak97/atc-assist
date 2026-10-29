from app.core import geo
from app.core.runway_geometry import RunwayGeometry
from app.schemas.runway import Airport

RAW = {"lat": 19.0, "lon": 72.9, "elev_ft": 10.0, "runways": [
    {"le": "09", "he": "27", "le_lat": 19.0, "le_lon": 72.88, "he_lat": 19.0, "he_lon": 72.92,
     "le_hdg": 90.0, "he_hdg": 270.0, "length_ft": 14000.0, "width_ft": 150.0}]}
G = RunwayGeometry(Airport.from_raw("TEST", RAW))


def test_final_assignment():
    lat, lon = geo.destination(19.0, 72.92, 90.0, 5.0)
    assert G.assign_arrival(float(lat), float(lon), 270.0) == "27"
    assert G.assign_arrival(float(lat), float(lon), 90.0) is None            # flying away
    la2, lo2 = geo.destination(float(lat), float(lon), 0.0, 3.0)
    assert G.assign_arrival(float(la2), float(lo2), 270.0) is None           # 3 nm off the centreline


def test_on_runway():
    assert G.on_runway(19.0, 72.90, 270.0) == "27"
    assert G.on_runway(19.0, 72.90, 90.0) == "09"
    assert G.on_runway(19.02, 72.90, 270.0) is None