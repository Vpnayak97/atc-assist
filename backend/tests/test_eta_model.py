import numpy as np
import pytest

from app.config import get_settings
from app.ml import features as F
from app.ml.eta_model import band_for, predict_eta
from app.ml.registry import Registry

BAND = {"bins": [2, 5, 10, 20, 35], "physics_below_nm": 5,
        "band": [[2, 5, -10, 10], [5, 10, -40, 50], [10, 20, -60, 70], [20, 35, -80, 90]]}


def test_band_lookup():
    assert band_for(3, BAND) == (-10, 10)
    assert band_for(5.0, BAND) == (-10, 10)        # (lo, hi] buckets
    assert band_for(5.01, BAND) == (-40, 50)
    assert band_for(40, BAND) is None and band_for(1, BAND) is None


def test_fallback_when_models_missing(tmp_path):
    reg = Registry(tmp_path)
    assert not any(s.loaded for s in reg.st.values())
    rows = [dict(dist_nm=12.0, phys_eta=300.0)]
    p = predict_eta(reg, rows, [1000.0])[0]
    assert p.source == "physics" and p.value == 300.0 and p.lo is None and p.hi is None


def test_helpers():
    assert F.approach_segment_ok([4000, 3000, 1500, 800, 300, 200, 150, 120, 100, 80, 60, 40],
                                 [30, 27, 24, 20, 16, 12, 9, 7, 5, 3, 2, 1]) is True
    assert F.approach_segment_ok([4000] * 12, [30] * 12) is False     # never gets low


@pytest.mark.skipif(not (get_settings().models_dir / "eta_resid.txt").exists(), reason="model files not present")
def test_real_models_load_and_feature_names_match():
    reg = Registry(get_settings().models_dir)
    for name, st in reg.st.items():
        assert st.loaded, (name, st.reason, reg.notes)
    for b in reg.vertical.values():
        assert b.feature_name() == F.M1_FEATS
    assert reg.eta_mid.feature_name() == reg.eta_meta["features"]
    rows = [F.eta_row(gs_d60=-5.0, agl_d60=-800.0, type_code="A320", lat=19.2, lon=73.1, alt_ft=4000.0,
                      on_ground=False, gs_kt=180.0, track=250.0, vrate_fpm=-700.0, ts=1_793_000_000.0,
                      airport=__import__("app.config", fromlist=["x"]).get_airport(),
                      headings=np.array([90.0, 270.0, 140.0, 320.0]))]
    p = predict_eta(reg, rows, [1_793_000_000.0])[0]
    assert 0 < p.value < 3600 and p.source in ("ml", "physics")