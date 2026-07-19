from typing import List, Dict
import datetime as dt
import pytz

DASHA_SEQUENCE = [
    ("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10),
    ("Mars", 7), ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17),
]
NAKSHATRA_LORDS = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"] * 3

def vimshottari_from_birth(moon_lon_deg: float, birth_dt_local: dt.datetime, tzinfo: pytz.BaseTzInfo) -> List[Dict]:
    span = 360.0 / 27.0
    nk_index0 = int((moon_lon_deg % 360.0) // span)  # 0..26
    lord = NAKSHATRA_LORDS[nk_index0]
    pos_in_nk = (moon_lon_deg % span) / span
    order = [x[0] for x in DASHA_SEQUENCE]
    years_map = {k: y for k, y in DASHA_SEQUENCE}
    start_idx = order.index(lord)
    cycle = order[start_idx:] + order[:start_idx]

    first_years_total = years_map[cycle[0]]
    balance_years = (1.0 - pos_in_nk) * first_years_total

    out = []
    cur_start = birth_dt_local
    first_end = cur_start + dt.timedelta(days=balance_years * 365.2425)
    out.append({"lord": cycle[0], "start": cur_start, "end": first_end, "years": balance_years})

    cur_start = first_end
    for i in range(1, 9):
        lord_i = cycle[i % 9]
        yrs = years_map[lord_i]
        cur_end = cur_start + dt.timedelta(days=yrs * 365.2425)
        out.append({"lord": lord_i, "start": cur_start, "end": cur_end, "years": float(yrs)})
        cur_start = cur_end

    return out[:10]

def antardasha_for_segment(md_lord: str, md_start: dt.datetime, md_end: dt.datetime) -> List[Dict]:
    total_days = (md_end - md_start).total_seconds() / 86400.0
    order = [x[0] for x in DASHA_SEQUENCE]
    years_map = {k: y for k, y in DASHA_SEQUENCE}
    start_idx = order.index(md_lord)
    cycle = order[start_idx:] + order[:start_idx]

    out = []
    cur = md_start
    for lord in cycle:
        frac = years_map[lord] / 120.0
        dur = total_days * frac
        end = cur + dt.timedelta(days=dur)
        out.append({"lord": lord, "start": cur, "end": end, "days": dur})
        cur = end
    return out
