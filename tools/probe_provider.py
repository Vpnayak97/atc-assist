"""Fetch one raw response, show its fields and save it as a test fixture.
Run from backend/:  python ../tools/probe_provider.py adsb_lol"""
import json
import sys
from pathlib import Path

import httpx

URLS = {"adsb_lol": "https://api.adsb.lol/v2/point/{lat}/{lon}/{r}",
        "airplanes_live": "https://api.airplanes.live/v2/point/{lat}/{lon}/{r}"}
name = sys.argv[1] if len(sys.argv) > 1 else "adsb_lol"
lat, lon, r = 19.0887, 72.8679, 60          # VABB
data = httpx.get(URLS[name].format(lat=lat, lon=lon, r=r), timeout=15).json()
ac = data.get("ac") or []
print(name, "aircraft:", len(ac), "| top-level keys:", list(data.keys()))
if ac:
    print("keys of first record:", sorted(ac[0].keys()))
    print(json.dumps(ac[0], indent=1))
    fx = Path("tests/fixtures"); fx.mkdir(parents=True, exist_ok=True)
    (fx / f"{name}_sample.json").write_text(json.dumps({"ac": ac[:40]}, indent=1))
    print("saved tests/fixtures/%s_sample.json" % name)