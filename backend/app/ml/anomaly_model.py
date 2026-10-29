from __future__ import annotations

import numpy as np
import pandas as pd


def score(reg, feats: dict) -> float:
    a = reg.anomaly
    row = {k: feats.get(k, a["medians"][k]) for k in a["features"]}
    x = pd.DataFrame([row])[a["features"]].replace([np.inf, -np.inf], np.nan).fillna(pd.Series(a["medians"]))
    return float(a["model"].decision_function(x)[0])


def threshold(reg) -> float:
    return float(reg.anomaly["thr"])


def outliers(reg, feats: dict, top: int = 3) -> list[dict]:
    """Features furthest from the training median, as a plain-language hint (not a model attribution)."""
    med = reg.anomaly["medians"]
    dev = {k: (feats[k] - med[k]) / (abs(med[k]) + 1.0) for k in med if k in feats}
    best = sorted(dev, key=lambda k: -abs(dev[k]))[:top]
    return [{"feature": k, "value": round(float(feats[k]), 1), "typical": round(float(med[k]), 1)} for k in best]