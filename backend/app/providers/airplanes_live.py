from app.providers.base import ReadsbProvider


class AirplanesLive(ReadsbProvider):
    name = "airplanes_live"
    base_url = "https://api.airplanes.live/v2"
    min_interval_s = 1.0   # documented limit: 1 request per second