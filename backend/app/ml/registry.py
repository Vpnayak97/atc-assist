from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("atc.ml")


@dataclass
class ModelStatus:
    name: str
    loaded: bool = False
    source: str = "fallback"            # "ml" or "fallback"
    version: Optional[str] = None
    reason: Optional[str] = None

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def _ver(path: Path, stem: str) -> str:
    return f"{stem}@{time.strftime('%Y-%m-%d', time.gmtime(path.stat().st_mtime))}"


class Registry:
    """Loads the Colab models. Anything missing or mismatched becomes an explicit fallback."""

    def __init__(self, models_dir: Path):
        self.dir = Path(models_dir)
        self.st = {k: ModelStatus(k) for k in ("vertical", "eta", "anomaly")}
        self.vertical: dict[int, Any] = {}
        self.eta_mid: Any = None
        self.eta_meta: dict = {}
        self.eta_band: Optional[dict] = None
        self.anomaly: Optional[dict] = None
        self.cards: dict = {}
        self.notes: list[str] = []
        self.sklearn_ok = True
        self._versions()
        self._vertical()
        self._eta()
        self._anomaly()
        self._cards()
        for s in self.st.values():
            log.info("model %s: %s (%s)", s.name, "loaded" if s.loaded else "FALLBACK", s.reason or s.version)

    def _versions(self):
        p = self.dir / "versions.json"
        if not p.exists():
            self.notes.append("versions.json missing; cannot verify library versions")
            return
        want = json.loads(p.read_text())
        have = {}
        for key, mod in (("sklearn", "sklearn"), ("lightgbm", "lightgbm"), ("numpy", "numpy")):
            try:
                have[key] = __import__(mod).__version__
            except Exception:
                have[key] = None
        for k, v in want.items():
            if have.get(k) != v:
                msg = f"{k}: trained with {v}, running {have.get(k)}"
                self.notes.append(msg)
                if k == "sklearn":                  # pickles are version-sensitive, LightGBM text models are not
                    self.sklearn_ok = False

    def _vertical(self):
        import lightgbm as lgb
        missing = []
        for H in (30, 60):
            p = self.dir / f"traj_ea_H{H}.txt"
            if p.exists():
                self.vertical[H] = lgb.Booster(model_file=str(p))
            else:
                missing.append(p.name)
        s = self.st["vertical"]
        s.loaded, s.source = bool(self.vertical), "ml" if self.vertical else "fallback"
        s.version = _ver(self.dir / "traj_ea_H30.txt", "traj_ea") if 30 in self.vertical else None
        s.reason = f"missing: {', '.join(missing)}" if missing else None

    def _eta(self):
        import lightgbm as lgb
        s, mp, meta_p = self.st["eta"], self.dir / "eta_resid.txt", self.dir / "eta_meta.json"
        if not (mp.exists() and meta_p.exists()):
            s.reason = "eta_resid.txt or eta_meta.json missing"
            return
        booster, meta = lgb.Booster(model_file=str(mp)), json.loads(meta_p.read_text())
        if booster.feature_name() != meta["features"]:
            s.reason = "feature list in model differs from eta_meta.json; refusing to load"
            return
        self.eta_mid, self.eta_meta = booster, meta
        s.loaded, s.source, s.version = True, "ml", _ver(mp, "eta_resid")
        bp = self.dir / "eta_band.json"
        if bp.exists():
            self.eta_band = json.loads(bp.read_text())
        else:
            s.reason = "eta_band.json missing: ETA shown without a band"

    def _anomaly(self):
        s, p = self.st["anomaly"], self.dir / "anomaly_iforest.joblib"
        if not p.exists():
            s.reason = "anomaly_iforest.joblib missing"
            return
        if not self.sklearn_ok:
            s.reason = "scikit-learn version differs from training; not loading the pickle"
            return
        import joblib
        d = joblib.load(p)
        if not all(k in d for k in ("model", "features", "thr", "medians")):
            s.reason = "unexpected joblib contents"
            return
        self.anomaly = d
        s.loaded, s.source, s.version = True, "ml", _ver(p, "anomaly_iforest")

    def _cards(self):
        p = self.dir / "model_cards.json"
        if p.exists():
            self.cards = json.loads(p.read_text())

    def status(self) -> dict:
        return {"models": {k: v.as_dict() for k, v in self.st.items()}, "notes": self.notes}