from app.config import get_settings
from app.core.separation import Separation, wake_category
from app.services.alert_service import AlertService
from app.schemas.alert import AlertType, Severity


def test_wake_and_matrix():
    assert [wake_category(t) for t in ("A388", "B77W", "A320", "C172", None)] == ["J", "H", "M", "L", "M"]
    sep = Separation(get_settings().data_dir, "ICAO")
    assert sep.required_nm("B77W", "A320") == (5.0, False)
    assert sep.required_nm("A320", None)[1] is True
    assert Separation(get_settings().data_dir, "RECAT_EU").scheme == "ICAO"


def test_alert_lifecycle():
    s = AlertService(grace_s=2)
    s.raise_("K", AlertType.CONFLICT, Severity.ADVISORY, ["a", "b"], "t", 100.0)
    assert s.ack("K") and s.alerts["K"].acknowledged
    s.raise_("K", AlertType.CONFLICT, Severity.WARNING, ["a", "b"], "t2", 101.0)
    assert not s.alerts["K"].acknowledged
    s.sweep(110.0)
    assert s.alerts["K"].cleared