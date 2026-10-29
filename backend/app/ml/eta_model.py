from __future__ import annotations

import numpy as np

from app.ml.features import eta_frame
from app.schemas.aircraft import Prediction


def band_for(dist_nm: float, cfg):
    if not cfg:
        return None
    for lo, hi, a, b in cfg["band"]:
        if lo < dist_nm <= hi:
            return a, b
    return None


def predict_eta(reg, rows: list[dict], computed_at: list[float]) -> list[Prediction]:
    """Hybrid ETA: physics below `physics_below_nm`, physics + LightGBM residual beyond.
    Band = empirical P10/P90 of the hybrid error per distance bucket (eta_band.json)."""
    if not rows:
        return []
    ml = reg.eta_mid is not None
    resid, contrib, cols = np.zeros(len(rows)), None, None
    if ml:
        cols = reg.eta_mid.feature_name()
        frame = eta_frame(rows, cols, reg.eta_meta["type_categories"])
        resid = reg.eta_mid.predict(frame)
        contrib = reg.eta_mid.predict(frame, pred_contrib=True)
    below = float((reg.eta_band or {}).get("physics_below_nm", 5.0))
    out = []
    for i, r in enumerate(rows):
        phys = float(r["phys_eta"])
        use_ml = ml and r["dist_nm"] >= below
        value = max(0.0, phys + float(resid[i])) if use_ml else max(0.0, phys)
        lo = hi = None
        bd = band_for(r["dist_nm"], reg.eta_band) if ml else None
        if bd:
            lo = max(0.0, value + bd[0])
            hi = max(lo, value + bd[1])
        why = []
        if use_ml:
            c = contrib[i][:-1]
            for j in np.argsort(-np.abs(c))[:3]:
                if abs(c[j]) >= 1.0:
                    why.append({"feature": cols[j], "contrib": round(float(c[j]), 1)})
        out.append(Prediction(
            kind="eta", value=round(value, 1),
            lo=None if lo is None else round(lo, 1), hi=None if hi is None else round(hi, 1),
            unit="s", source="ml" if use_ml else "physics",
            model_version=reg.st["eta"].version if use_ml else None,
            physics_value=round(phys, 1), explanation=why, computed_at=computed_at[i]))
    return out