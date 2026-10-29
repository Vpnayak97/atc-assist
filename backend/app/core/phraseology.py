from __future__ import annotations

import math
import re

DIGITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
PHON = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet", "kilo",
                 "lima", "mike", "november", "oscar", "papa", "quebec", "romeo", "sierra", "tango", "uniform",
                 "victor", "whiskey", "xray", "yankee", "zulu"]))
RT = {"IGO": "IndiGo", "AIC": "Air India", "AXB": "Express India", "AKJ": "Akasa Air", "VTI": "Vistara",
      "SEJ": "SpiceJet", "LLR": "Alliance", "UAE": "Emirates", "QTR": "Qatari", "ETD": "Etihad", "SVA": "Saudia",
      "GFA": "Gulf Air", "OMA": "Oman Air", "KAC": "Kuwaiti", "FDB": "Flydubai", "ABY": "Arabia", "ALK": "SriLankan",
      "SIA": "Singapore", "THA": "Thai", "MAS": "Malaysian", "CPA": "Cathay", "BAW": "Speedbird", "VIR": "Virgin",
      "DLH": "Lufthansa", "AFR": "Air France", "KLM": "KLM", "THY": "Turkish", "ETH": "Ethiopian",
      "UAL": "United", "AAL": "American", "DAL": "Delta", "FDX": "FedEx", "UPS": "UPS", "CLX": "Cargolux"}


def digits(s) -> str:
    return " ".join(DIGITS[int(c)] for c in str(s) if c.isdigit())


def spell(s: str) -> str:
    return " ".join(DIGITS[int(c)] if c.isdigit() else PHON[c] for c in (s or "").upper() if c.isdigit() or c in PHON)


def callsign_speech(callsign, reg=None, hexcode=None) -> str:
    cs = (callsign or "").strip().upper()
    m = re.fullmatch(r"([A-Z]{3})(\d{1,4})([A-Z]{0,2})", cs)
    if m:
        pre, num, suf = m.groups()
        return " ".join(x for x in (RT.get(pre) or spell(pre), digits(num), spell(suf)) if x)
    return spell(cs) or spell(reg or "") or "unidentified aircraft"


def heading_speech(h) -> str:
    return digits(f"{(int(round(h)) % 360) or 360:03d}")


def altitude_words(ft) -> str:
    ft = int(round(ft / 100.0)) * 100
    th, hu = ft // 1000, (ft % 1000) // 100
    parts = ([f"{digits(th)} thousand"] if th else []) + ([f"{DIGITS[hu]} hundred"] if hu else [])
    return " ".join(parts) or "zero"


def level_speech(alt_ft, transition_ft) -> str:
    if alt_ft > transition_ft:
        return f"flight level {digits(f'{round(alt_ft / 100):03d}')}"
    return f"altitude {altitude_words(alt_ft)} feet"


def short_cs(r: dict) -> str:
    return r.get("callsign") or r["hex"].upper()


def spoken_cs(r: dict) -> str:
    return callsign_speech(r.get("callsign"), r.get("reg"), r["hex"])


def traffic_info(own: dict, other: dict) -> str:
    dx, dy = other["x"] - own["x"], other["y"] - own["y"]
    rel = (math.degrees(math.atan2(dx, dy)) - own["trk"]) % 360.0
    clock = int(round(rel / 30.0)) % 12 or 12
    miles = max(1, int(round(math.hypot(dx, dy))))
    dz = (other["alt"] or 0.0) - (own["alt"] or 0.0)
    rel_alt = "same level" if abs(dz) < 300 else f"{altitude_words(abs(dz))} feet {'above' if dz > 0 else 'below'}"
    return f"Traffic {clock} o'clock, {miles} miles, {rel_alt}."


def build_instruction(opt: dict, own: dict, other: dict, transition_ft: float) -> tuple[str, str]:
    cs, sc, kind = short_cs(own), spoken_cs(own), opt["kind"]
    if kind == "heading":
        side, h = ("left" if opt["delta"] < 0 else "right"), int(opt["value"])
        text, short = f"{sc}, turn {side} heading {heading_speech(h)}.", f"{cs} TURN {side.upper()} HDG {h:03d}"
    elif kind == "level":
        tgt = float(opt["value"])
        verb = "climb" if tgt > own["alt"] else "descend"
        label = f"FL{round(tgt / 100):03d}" if tgt > transition_ft else f"{int(tgt)} FT"
        text, short = f"{sc}, {verb} {level_speech(tgt, transition_ft)}.", f"{cs} {verb.upper()} {label}"
    else:
        n = int(opt["value"])
        text, short = f"{sc}, reduce speed by {digits(n)} knots.", f"{cs} REDUCE SPEED {n} KT"
    return f"{text} {traffic_info(own, other)}", short