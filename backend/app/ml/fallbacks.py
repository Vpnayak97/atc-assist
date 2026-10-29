def physics_eta_s(dist_nm: float, gs_kt: float, min_gs_kt: float = 80.0) -> float:
    return dist_nm / max(gs_kt, min_gs_kt) * 3600.0


def physics_alt(alt_ft: float, vrate_fpm: float, horizon_s: float, floor_ft: float = 0.0) -> float:
    return max(floor_ft, alt_ft + vrate_fpm * horizon_s / 60.0)