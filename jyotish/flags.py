"""
jyotish/flags.py
----------------
Planetary dignity and condition flags.

Provides:
  compute_planet_flags(planets, sun_lon, panchang_module) -> Dict[str, str]
  bhava_lordship_block(asc_deg, planet_houses, planets, panchang_module) -> str
"""
from typing import Dict

# Traditional combustion orbs (degrees from Sun)
COMBUST_ORB: Dict[str, float] = {
    "Mercury": 12, "Venus": 10, "Mars": 17,
    "Jupiter": 11, "Saturn": 15, "Moon": 12,
}

# Exaltation signs (0-indexed: 0=Aries … 11=Pisces)
EXALT_SIGN: Dict[str, int] = {
    "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
    "Jupiter": 3, "Venus": 11, "Saturn": 6,
}
DEBIL_SIGN: Dict[str, int] = {k: (v + 6) % 12 for k, v in EXALT_SIGN.items()}

OWN_SIGNS: Dict[str, list] = {
    "Sun":     ["Simha (Leo)"],
    "Moon":    ["Karka (Cancer)"],
    "Mars":    ["Mesha (Aries)", "Vrishchika (Scorpio)"],
    "Mercury": ["Mithuna (Gemini)", "Kanya (Virgo)"],
    "Jupiter": ["Dhanu (Sagittarius)", "Meena (Pisces)"],
    "Venus":   ["Vrishabha (Taurus)", "Tula (Libra)"],
    "Saturn":  ["Makara (Capricorn)", "Kumbha (Aquarius)"],
}

# Moolatrikona ranges: (rashi_name, degree_start, degree_end)
MT_RANGES: Dict[str, tuple] = {
    "Sun":     ("Simha (Leo)",          0.0, 20.0),
    "Moon":    ("Vrishabha (Taurus)",   4.0, 20.0),
    "Mars":    ("Mesha (Aries)",        0.0, 12.0),
    "Mercury": ("Kanya (Virgo)",       16.0, 20.0),
    "Jupiter": ("Dhanu (Sagittarius)",  0.0, 10.0),
    "Venus":   ("Tula (Libra)",         0.0, 15.0),
    "Saturn":  ("Kumbha (Aquarius)",    0.0, 20.0),
}


def _sign_index(lon: float) -> int:
    return int((lon % 360.0) // 30)


def _exalt_status(name: str, lon: float) -> str:
    s = _sign_index(lon)
    if name in EXALT_SIGN:
        if s == EXALT_SIGN[name]:
            return "Exalted"
        if s == DEBIL_SIGN[name]:
            return "Debilitated"
    return ""


def _is_combust(name: str, lon: float, sun_lon: float) -> bool:
    if name not in COMBUST_ORB:
        return False
    diff = abs(((lon - sun_lon + 180) % 360) - 180)
    return diff <= COMBUST_ORB[name]


def _is_retro(speed: float) -> bool:
    return speed < 0


def compute_planet_flags(planets: dict, sun_lon: float, panchang_module) -> Dict[str, str]:
    """Return a dict mapping planet name -> comma-separated flag string."""
    flags: Dict[str, str] = {}
    for nm, data in planets.items():
        status = []
        lonv = data["lon"] % 360.0
        rashi = panchang_module.rashi_name(lonv)
        if _is_retro(data["speed"]):
            status.append("R")
        if _is_combust(nm, lonv, sun_lon):
            status.append("Combust")
        ed = _exalt_status(nm, lonv)
        if ed:
            status.append(ed)
        if rashi in OWN_SIGNS.get(nm, []):
            status.append("Own")
        mt = MT_RANGES.get(nm)
        if mt and rashi == mt[0]:
            deg_in_sign = lonv % 30.0
            if mt[1] <= deg_in_sign <= mt[2]:
                status.append("Moolatrikona")
        flags[nm] = ", ".join(status)
    return flags


_SIGN_LORD_MAP: Dict[int, str] = {
    0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon",
    4: "Sun",  5: "Mercury", 6: "Venus", 7: "Mars",
    8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter",
}


def bhava_lordship_block(asc_deg: float, planet_houses: dict,
                          planets: dict, panchang_module) -> str:
    """Return a multi-line string of H1-H12 lord → house placements."""
    asc_sign = int((asc_deg % 360.0) // 30)
    lines = []
    for h in range(1, 13):
        sign_idx = (asc_sign + (h - 1)) % 12
        lord = _SIGN_LORD_MAP[sign_idx]
        lord_h = planet_houses.get(lord, "?")
        lord_rashi = panchang_module.rashi_name(planets[lord]["lon"]) if lord in planets else "-"
        lines.append(f"H{h} lord {lord} -> House {lord_h} ({lord_rashi})")
    return "\n".join(lines)
