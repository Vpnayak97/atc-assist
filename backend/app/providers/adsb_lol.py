from app.providers.base import ReadsbProvider


class AdsbLol(ReadsbProvider):
    name = "adsb_lol"
    base_url = "https://api.adsb.lol/v2"
    min_interval_s = 1.0