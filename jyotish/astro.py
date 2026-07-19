import datetime as dt
from typing import Dict, List
import pytz
import swisseph as swe

AYANAMSA_MAP = {
    "Lahiri": swe.SIDM_LAHIRI,
    "Krishnamurti": swe.SIDM_KRISHNAMURTI,
    "Raman": swe.SIDM_RAMAN,
    "Fagan/Bradley": swe.SIDM_FAGAN_BRADLEY,
}

HOUSE_CODES = {
    "Placidus": b"P",
    "Sripati (Porphyry)": b"O",
    "Whole Sign": b"W",
}

swe.set_ephe_path(".")

PLANETS_BASE = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
    "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS, "Saturn": swe.SATURN,
}

def set_sidereal_mode(ayanamsa_name: str):
    swe.set_sid_mode(AYANAMSA_MAP.get(ayanamsa_name, swe.SIDM_LAHIRI), 0, 0)

def to_julday_ut(dt_local: dt.datetime, tzinfo: pytz.BaseTzInfo) -> float:
    if dt_local.tzinfo is None:
        dt_local = tzinfo.localize(dt_local)
    dt_utc = dt_local.astimezone(pytz.utc)
    hour = dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour, swe.GREG_CAL)

def get_ayanamsa(jd_ut: float) -> float:
    return swe.get_ayanamsa_ut(jd_ut)

def _calc_ut_robust(jd_ut, body, flags):
    res = swe.calc_ut(jd_ut, body, flags)
    if isinstance(res, (tuple, list)) and len(res) == 2 and hasattr(res[0], '__len__'):
        (lon, lat, dist, lon_sp, lat_sp, dist_sp), _ = res
    else:
        lon, lat, dist, lon_sp, lat_sp, dist_sp = res[:6]
    return lon % 360.0, lon_sp

def sidereal_longitude(jd_ut: float, body: int):
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    try:
        return _calc_ut_robust(jd_ut, body, flags)
    except Exception:
        return _calc_ut_robust(jd_ut, body, swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED)

def all_planets_sidereal(jd_ut: float, ayanamsa_name: str = "Lahiri", node_type: str = "True"):
    set_sidereal_mode(ayanamsa_name)
    out = {}
    for name, pid in PLANETS_BASE.items():
        lon, sp = sidereal_longitude(jd_ut, pid)
        out[name] = {"lon": lon, "speed": sp}
    node_pid = swe.MEAN_NODE if node_type.lower().startswith("mean") else swe.TRUE_NODE
    lon, sp = sidereal_longitude(jd_ut, node_pid)
    out["Rahu"] = {"lon": lon, "speed": sp}
    out["Ketu"] = {"lon": (lon + 180.0) % 360.0, "speed": -sp}
    return out

def ascendant_sidereal(jd_ut: float, lat_deg: float, lon_deg: float, ayanamsa_name: str = "Lahiri") -> float:
    set_sidereal_mode(ayanamsa_name)
    cusps, ascmc = swe.houses_ex(jd_ut, lat_deg, lon_deg, b"P", 0)
    asc_trop = ascmc[0] % 360.0
    ayan = get_ayanamsa(jd_ut)
    return (asc_trop - ayan) % 360.0

def houses_sidereal(jd_ut: float, lat_deg: float, lon_deg: float, ayanamsa_name: str, house_system_name: str) -> List[float]:
    """Whole Sign computed from Lagna; others via Swiss then siderealized."""
    set_sidereal_mode(ayanamsa_name)
    if house_system_name == "Whole Sign":
        asc_sid = ascendant_sidereal(jd_ut, lat_deg, lon_deg, ayanamsa_name)
        asc_sign_start = int((asc_sid % 360.0) // 30) * 30.0
        return [(asc_sign_start + i*30.0) % 360.0 for i in range(12)]
    hsys = HOUSE_CODES.get(house_system_name, b"P")
    cusps, ascmc = swe.houses_ex(jd_ut, lat_deg, lon_deg, hsys, 0)
    ayan = get_ayanamsa(jd_ut)
    sid = []
    for i in range(1, 13):
        c = cusps[i] if i < len(cusps) else cusps[-1]
        sid.append(((c - ayan) % 360.0))
    return sid

def which_house_whole_sign(asc_deg: float, lon_deg: float) -> int:
    asc_sign = int((asc_deg % 360.0) // 30)
    sign = int((lon_deg % 360.0) // 30)
    return ((sign - asc_sign) % 12) + 1

def which_house_from_cusps(lon_deg: float, cusps_sidereal: List[float]) -> int:
    c1 = cusps_sidereal[0]
    bounds = [((c - c1) % 360.0) for c in cusps_sidereal]
    idx_sorted = list(range(12))
    idx_sorted.sort(key=lambda i: bounds[i])
    segments = []
    for i in range(12):
        a = bounds[idx_sorted[i]]
        b = bounds[idx_sorted[(i+1)%12]]
        if b <= a: b += 360.0
        segments.append((a, b, idx_sorted[i]+1))
    p = ((lon_deg - c1) % 360.0)
    for a, b, h in segments:
        if a <= p < b:
            return h
    return 12


def sunrise_sunset_local(date_local: dt.date, lat: float, lon: float, tzinfo: pytz.BaseTzInfo):
    """Return local sunrise and sunset datetimes for the civil date."""
    noon_local = tzinfo.localize(dt.datetime(date_local.year, date_local.month, date_local.day, 12, 0, 0))
    jd_noon = to_julday_ut(noon_local, tzinfo)

    # Correct argument order: (jd_ut, ipl, lon, lat, rsmi)
    rf, jd_rise = swe.rise_trans(jd_noon, swe.SUN, lon, lat, swe.CALC_RISE | swe.BIT_DISC_CENTER)
    sf, jd_set  = swe.rise_trans(jd_noon, swe.SUN, lon, lat, swe.CALC_SET  | swe.BIT_DISC_CENTER)

    def jd_to_local(jd):
        y, m, d, h = swe.revjul(jd, swe.GREG_CAL)
        hh = int(h); mm = int((h - hh)*60); ss = int((((h - hh)*60) - mm)*60)
        dt_utc = pytz.utc.localize(dt.datetime(y, m, d, hh, mm, ss))
        return dt_utc.astimezone(tzinfo)

    return jd_to_local(jd_rise), jd_to_local(jd_set)
