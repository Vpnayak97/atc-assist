from __future__ import annotations

import numpy as np
import pandas as pd


def predict_vertical(reg, rows: list[dict]) -> dict[int, np.ndarray]:
    """Altitude residual (ft) per horizon, to add to the vrate dead-reckoned altitude."""
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    return {H: b.predict(df[b.feature_name()]) for H, b in reg.vertical.items()}