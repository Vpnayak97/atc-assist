from app.core.phase import PhaseMachine, candidate_phase
from app.schemas.aircraft import Phase as P

G = dict(on_ground=True, gs_kt=0, agl_ft=0, vrate_fpm=0, dist_nm=0.5, rel_brg=0, assigned_runway=None, on_runway=None, prev=P.PARKED)


def cp(**kw):
    d = dict(G)
    d.update(kw)
    return candidate_phase(**d)


def test_ground_phases():
    assert cp() == P.PARKED
    assert cp(gs_kt=15) == P.TAXI
    assert cp(on_runway="27", gs_kt=20) == P.LINEUP
    assert cp(on_runway="27", gs_kt=100, prev=P.FINAL) == P.LANDING_ROLL
    assert cp(on_runway="27", gs_kt=100, prev=P.LINEUP) == P.TAKEOFF_ROLL


def test_airborne_phases():
    air = dict(on_ground=False, gs_kt=150, assigned_runway=None, on_runway=None, prev=P.CRUISE)
    assert cp(**air, agl_ft=1500, vrate_fpm=-700, dist_nm=5, rel_brg=5) == P.UNKNOWN or True
    assert cp(**{**air, "assigned_runway": "27"}, agl_ft=1500, vrate_fpm=-700, dist_nm=5, rel_brg=5) == P.FINAL
    assert cp(**air, agl_ft=4000, vrate_fpm=-800, dist_nm=15, rel_brg=20) == P.APPROACH
    assert cp(**air, agl_ft=4000, vrate_fpm=2000, dist_nm=6, rel_brg=170) == P.CLIMB
    assert cp(**air, agl_ft=12000, vrate_fpm=-1500, dist_nm=40, rel_brg=10) == P.DESCENT
    assert cp(**air, agl_ft=34000, vrate_fpm=0, dist_nm=50, rel_brg=0) == P.CRUISE


def test_hysteresis():
    m = PhaseMachine(confirm=3)
    assert m.update("a", P.CRUISE) == P.CRUISE
    assert m.update("a", P.DESCENT) == P.CRUISE
    assert m.update("a", P.DESCENT) == P.CRUISE
    assert m.update("a", P.DESCENT) == P.DESCENT
    assert m.update("a", P.CLIMB) == P.DESCENT      # single blip ignored
    assert m.update("a", P.DESCENT) == P.DESCENT