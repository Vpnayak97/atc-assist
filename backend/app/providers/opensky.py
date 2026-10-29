import math
import time

from app.providers.base import Provider, _num
from app.schemas.aircraft import RawSample

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
STATES_URL = "https://opensky-network.org/api/states/all"
M_TO_FT, MS_TO_KT, MS_TO_FPM = 3.28084, 1.943844, 196.8504


class OpenSky(Provider):
    """Low-rate fallback. Anonymous: 400 credits/day, so one call every 4 min.
    With OAuth2 client credentials: 4,000/day, so one call per 30 s is affordable."""
    name = "opensky"
    min_interval_s = 1.0

    def __init__(self, open_after=3, probe_after_s=60.0, client_id="", client_secret=""):
        super().__init__(open_after, probe_after_s)
        self.client_id, self.client_secret = client_id, client_secret
        self.poll_interval_s = 30.0 if (client_id and client_secret) else 240.0
        self._token, self._token_exp = None, 0.0

    async def _headers(self, client) -> dict:
        if not (self.client_id and self.client_secret):
            return {}
        if self._token is None or time.time() > self._token_exp - 60:
            r = await client.post(TOKEN_URL, data={"grant_type": "client_credentials",
                                                   "client_id": self.client_id,
                                                   "client_secret": self.client_secret})
            r.raise_for_status()
            j = r.json()
            self._token = j["access_token"]
            self._token_exp = time.time() + float(j.get("expires_in", 1800))
        return {"Authorization": f"Bearer {self._token}"}

    async def _fetch(self, client, lat, lon, radius_nm):
        dlat = radius_nm / 60.0
        dlon = radius_nm / (60.0 * max(math.cos(math.radians(lat)), 0.1))
        params = {"lamin": lat - dlat, "lamax": lat + dlat, "lomin": lon - dlon, "lomax": lon + dlon}
        resp = await client.get(STATES_URL, params=params, headers=await self._headers(client))
        resp.raise_for_status()
        data, fetched = resp.json(), time.time()
        out = []
        for s in data.get("states") or []:
            if len(s) < 17:
                continue
            lo, la = _num(s[5]), _num(s[6])
            if lo is None or la is None:
                continue
            tp = _num(s[3])
            baro, geom = _num(s[7]), _num(s[13])
            gs, vr = _num(s[9]), _num(s[11])
            ground = bool(s[8])
            out.append(RawSample(
                hex=str(s[0]).lower(), callsign=(s[1] or "").strip() or None,
                lat=la, lon=lo,
                alt_baro_ft=None if (ground or baro is None) else baro * M_TO_FT,
                alt_geom_ft=None if geom is None else geom * M_TO_FT,
                gs_kt=None if gs is None else gs * MS_TO_KT, track_deg=_num(s[10]),
                vrate_fpm=None if vr is None else vr * MS_TO_FPM,
                squawk=s[14] or None, on_ground=ground,
                seen_pos_s=max(0.0, fetched - tp) if tp else None,
                source=self.name, fetched_at=fetched))
        return out