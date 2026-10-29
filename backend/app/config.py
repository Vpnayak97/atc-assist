
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas.runway import Airport

BASE_DIR = Path(__file__).resolve().parents[1]  # .../backend


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ATC_", extra="ignore")

    # --- airport and scheme (decisions from the direction document, section 18) ---
    airport: str = "VABB"
    separation_scheme: str = "ICAO"          # "ICAO" or "RECAT_EU"

    # --- ingest ---
    query_radius_nm: float = 60.0
    fetch_interval_s: float = 30.0           # floor enforced in fetch loop (5 s)
    provider_order: list[str] = ["adsb_lol", "adsb_fi", "airplanes_live", "opensky"]
    opensky_client_id: str = ""        # set via .env: ATC_OPENSKY_CLIENT_ID
    opensky_client_secret: str = ""    # set via .env: ATC_OPENSKY_CLIENT_SECRET
    max_sample_age_s: float = 60.0
    http_timeout_s: float = 8.0
    circuit_open_after: int = 3
    circuit_probe_after_s: float = 60.0

    # --- track lifecycle ---
    stale_drop_s: float = 120.0
    stale_drop_ground_s: float = 300.0
    extrapolation_limit_s: float = 30.0
    max_plausible_gs_kt: float = 700.0
    max_position_jump_kt: float = 800.0

    # --- separation minima (configuration, not authority: match local procedures) ---
    radar_sep_nm: float = 5.0
    radar_sep_terminal_nm: float = 3.0
    vertical_sep_ft: float = 1000.0
    use_terminal_minima: bool = False

    # --- ETA / ML ---
    physics_eta_below_nm: float = 5.0        # inside this, physics ETA is used
    min_gs_for_eta_kt: float = 80.0

    # --- planner ---
    planner_interval_s: float = 30.0
    planner_horizon_min: float = 40.0
    freeze_window_s: float = 300.0
    max_delay_s: float = 600.0

    # --- conflict / vectoring / advisories ---
    conflict_lookahead_s: float = 180.0
    conflict_step_s: float = 5.0
    conflict_warn_s: float = 45.0
    conflict_caution_s: float = 90.0
    terminal_radius_nm: float = 30.0
    max_conflict_age_s: float = 20.0
    conflict_confirm_ticks: int = 3
    conflict_clear_ticks: int = 5
    vert_extrap_s: float = 60.0
    pilot_delay_s: float = 5.0
    std_turn_dps: float = 3.0
    climb_fpm: float = 1500.0
    descend_fpm: float = 1500.0
    min_vector_alt_agl_ft: float = 3000.0
    max_level_ft: float = 41000.0
    resolution_margin: float = 1.15
    advisory_interval_s: float = 3.0
    advisory_valid_s: float = 120.0
    transition_altitude_ft: float = 4000.0     # verify for your airport
    magnetic_variation_deg: float = 0.0        # east positive; METAR wind is magnetic
    metar_interval_s: float = 300.0

    # --- paths ---
    data_dir: Path = BASE_DIR / "data"
    models_dir: Path = BASE_DIR / "models"
    db_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'atc.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def load_airports() -> dict[str, Airport]:
    raw = json.loads((get_settings().data_dir / "airports.json").read_text(encoding="utf-8"))
    return {icao: Airport.from_raw(icao, d) for icao, d in raw.items()}


def get_airport() -> Airport:
    s = get_settings()
    airports = load_airports()
    if s.airport not in airports:
        raise KeyError(f"Airport {s.airport} not in airports.json ({sorted(airports)})")
    return airports[s.airport]
