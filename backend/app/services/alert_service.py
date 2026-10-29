from __future__ import annotations

from app.schemas.alert import Alert, AlertType, Severity

RANK = {"ADVISORY": 1, "CAUTION": 2, "WARNING": 3}


class AlertService:
    def __init__(self, grace_s: float = 6.0):
        self.alerts: dict[str, Alert] = {}
        self.seen: dict[str, float] = {}
        self.grace_s = grace_s

    def raise_(self, key: str, type_: AlertType, severity: Severity, flights: list[str], text: str,
               now: float, meta: dict | None = None) -> Alert:
        a = self.alerts.get(key)
        if a is None or a.cleared:
            a = Alert(id=key, type=type_, severity=severity, flights=flights, text=text,
                      created_at=now, updated_at=now, meta=meta or {})
            self.alerts[key] = a
        else:
            if RANK[severity.value] > RANK[a.severity.value]:
                a.acknowledged = False                           # escalation re-opens an acknowledged alert
            a.severity, a.text, a.flights, a.updated_at = severity, text, flights, now
            a.meta = meta or a.meta
        self.seen[key] = now
        return a

    def sweep(self, now: float) -> None:
        for key, a in list(self.alerts.items()):
            if not a.cleared and now - self.seen.get(key, 0.0) > self.grace_s:
                a.cleared, a.updated_at = True, now
            elif a.cleared and now - a.updated_at > 30.0:
                del self.alerts[key]
                self.seen.pop(key, None)

    def ack(self, key: str) -> bool:
        a = self.alerts.get(key)
        if a is None:
            return False
        a.acknowledged = True
        return True

    def snapshot(self) -> list[dict]:
        items = sorted(self.alerts.values(), key=lambda a: (-RANK[a.severity.value], a.created_at))
        return [a.model_dump(mode="json") for a in items]