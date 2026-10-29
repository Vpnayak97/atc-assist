from __future__ import annotations

from app.core.phraseology import callsign_speech, short_cs
from app.schemas.aircraft import Priority

SQUAWK = {"7500": "unlawful interference", "7600": "radio failure", "7700": "general emergency"}
FIELD = {"general": "general emergency", "nordo": "radio failure", "unlawful": "unlawful interference",
         "downed": "aircraft down"}
MEDICAL = {"lifeguard": "medical priority", "minfuel": "minimum fuel"}


class EmergencyService:
    def __init__(self):
        self.manual_emg: dict[str, str] = {}
        self.manual_pri: dict[str, Priority] = {}
        self.count: dict[str, int] = {}

    def scan(self, tracker) -> list[dict]:
        out = []
        for hx, t in tracker.tracks.items():
            s = t.sample
            code = SQUAWK.get(s.squawk or "")
            self.count[hx] = self.count.get(hx, 0) + 1 if code else 0      # squawk must persist 3 ticks
            reason, med = self.manual_emg.get(hx), MEDICAL.get(s.emergency or "")
            if not reason and self.count[hx] >= 3:
                reason = f"squawk {s.squawk}, {code}"
            if not reason and s.emergency in FIELD:
                reason = FIELD[s.emergency]
            t.emergency = reason
            t.priority = (Priority.EMERGENCY if reason else self.manual_pri.get(hx) or
                          (Priority.MEDICAL if med else Priority.NORMAL))
            if reason or med:
                name = short_cs({"callsign": t.callsign, "hex": hx})
                what = reason or med
                out.append({"key": f"EMG:{hx}", "hex": hx, "severity": "WARNING" if reason else "CAUTION",
                            "text": f"{name}: {what}",
                            "speech": f"{'Emergency' if reason else 'Priority'}. "
                                      f"{callsign_speech(t.callsign, s.registration, hx)}, {what}."})
        return out