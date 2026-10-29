import json
from pathlib import Path

import numpy as np
import pytest

from app.config import load_airports
from app.ml import features as F

FX = Path(__file__).parent / "fixtures"


def test_rw_off():
    h = np.array([91.0, 271.0])
    assert F.rw_off([91.0, 271.0, 181.0, 359.0], h) == pytest.approx([0.0, 0.0, 90.0, 88.0])
    assert F.rw_off([10.0], np.array([])) == pytest.approx([90.0])


def test_rel_bearing_signs():
    # airport due east of an aircraft heading north: airport is 90 deg to the right
    assert F.rel_bearing(0.0, 0.0, 0.0, 0.0, 1.0) == pytest.approx(90.0, abs=0.01)
    assert F.rel_bearing(0.0, 0.0, 90.0, 0.0, 1.0) == pytest.approx(0.0, abs=0.01)   # dead ahead


def test_delta_60_interp_and_clamp():
    assert F.delta_60([0, 30, 60, 90], [100, 110, 120, 130], 90, 130) == pytest.approx(20.0)
    assert F.delta_60([0, 30], [100, 110], 30, 110) == pytest.approx(10.0)            # clamped to oldest


def test_eta_frame_maps_unknown_type_to_other():
    cats = ["A320", "B738", "other"]
    row = F.eta_row(gs_d60=0, agl_d60=0, type_code="C172", lat=19.2, lon=72.9, alt_ft=3000, on_ground=False,
                    gs_kt=150, track=270, vrate_fpm=-700, ts=1_700_000_000, airport=load_airports()["VABB"],
                    headings=np.array([90.0, 270.0]))
    df = F.eta_frame([row], ["dist_nm", "phys_eta", "type_c"], cats)
    assert df["type_c"].iloc[0] == "other" and list(df["type_c"].cat.categories) == cats


@pytest.mark.skipif(not (FX / "golden_m1.json").exists(), reason="export golden rows from Colab first")
def test_m1_parity_with_colab():
    rows = json.loads((FX / "golden_m1.json").read_text())
    ap = load_airports()
    for r in rows:
        a = ap[r["airport"]]
        got = F.m1_row(lat=r["lat"], lon=r["lon"], alt_ft=r["alt_ft"], on_ground=bool(r.get("on_ground", False)),
                       gs_kt=r["gs_kt"], track=r["track"], vrate_fpm=r["vrate_fpm"], ts=r["ts"],
                       airport=a, headings=F.runway_headings(a))
        for k in F.M1_FEATS:
            assert got[k] == pytest.approx(r[k], rel=1e-3, abs=0.05), (r["airport"], k)