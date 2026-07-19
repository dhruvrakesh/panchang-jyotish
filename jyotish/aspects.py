"""
jyotish/aspects.py
------------------
Aspect and Drishti calculations.

Provides:
  geo_aspects(planets)              -> list of dicts (Western geometric aspects)
  classical_parasari_drishti(...)   -> list of (planet, target_sign_idx, "Drishti")
  drishti_rows(planets, panchang)   -> list of dicts ready for a DataFrame
"""
from typing import Dict, List, Tuple


_GEO_TYPES: List[Tuple[float, str, float]] = [
    (0,   "Conj",  8),
    (60,  "Sext",  4),
    (90,  "Square", 6),
    (120, "Trine", 6),
    (180, "Opp",   8),
]

_EXTRA_ASPECTS: Dict[str, List[int]] = {
    "Jupiter": [5, 9],
    "Mars":    [4, 8],
    "Saturn":  [3, 10],
}
_DRISHTI_EXCLUDE = {"Rahu", "Ketu"}


def geo_aspects(planets: dict) -> List[dict]:
    """Western Ptolemaic aspects with degree orbs."""
    names = list(planets.keys())
    rows: List[dict] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a = planets[names[i]]["lon"] % 360.0
            b = planets[names[j]]["lon"] % 360.0
            d = abs(((a - b + 180) % 360.0) - 180)
            for ang, tag, orb in _GEO_TYPES:
                if abs(d - ang) <= orb:
                    rows.append({
                        "A": names[i], "B": names[j],
                        "type": tag, "delta": round(d - ang, 2),
                    })
                    break
    return rows


def classical_parasari_drishti(
    planet_sign_idx: Dict[str, int]
) -> List[Tuple[str, int, str]]:
    """
    Strict Parashari graha-drishti (BPHS, Graha-dristi Adhyaya):
      - All planets aspect the 7th sign.
      - Jupiter additionally aspects the 5th and 9th.
      - Mars additionally aspects the 4th and 8th.
      - Saturn additionally aspects the 3rd and 10th.
    Rahu and Ketu are excluded (they have no Parashari drishti).
    Returns list of (aspecting_planet, target_sign_0based, type_label) where
    type_label names the drishti, e.g. "7th (full)" or "4th (special)".
    (J6b, 2026-07-19: labels differentiated — previously every row said just
    "Drishti", hiding which drishti it was.)
    """
    _ORD = {3: "3rd", 4: "4th", 5: "5th", 7: "7th", 8: "8th", 9: "9th", 10: "10th"}
    rows: List[Tuple[str, int, str]] = []
    for planet, sign_idx in planet_sign_idx.items():
        if planet in _DRISHTI_EXCLUDE:
            continue
        offsets = [7] + _EXTRA_ASPECTS.get(planet, [])
        for off in offsets:
            target_sign = (sign_idx + off - 1) % 12
            kind = "full" if off == 7 else "special"
            rows.append((planet, target_sign, f"{_ORD[off]} ({kind})"))
    return rows


def drishti_rows(planets: dict, panchang_module) -> List[dict]:
    """Convenience wrapper returning drishti as list of dicts for DataFrame."""
    sign_idx = {k: int((v["lon"] % 360.0) // 30) for k, v in planets.items()}
    sign_names = [panchang_module.rashi_name(i * 30.0) for i in range(12)]
    raw = classical_parasari_drishti(sign_idx)
    return [{"A": p, "B": sign_names[s], "type": t} for p, s, t in raw]
