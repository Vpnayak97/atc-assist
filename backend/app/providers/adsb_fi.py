import time

from app.providers.base import Provider, parse_readsb


class AdsbFi(Provider):
    """adsb.fi open data: 1 req/s, personal non-commercial use, attribution required."""
    name = "adsb_fi"
    min_interval_s = 1.0

    async def _fetch(self, client, lat, lon, radius_nm):
        url = f"https://opendata.adsb.fi/api/v2/lat/{lat:.4f}/lon/{lon:.4f}/dist/{radius_nm:.0f}"
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return parse_readsb(data.get("ac") or data.get("aircraft") or [], self.name, time.time())