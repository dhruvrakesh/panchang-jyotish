from typing import List, Dict
import datetime as dt
import pytz

DASHA_SEQUENCE = [
    ("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10),
    ("Mars", 7), ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17),
]
NAKSHATRA_LORDS = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"] * 3

# Year length used to convert dasha years to days. 365.25 (Julian year) is the
# most common convention in Jyotish software; documented here as an explicit,
# auditable choice. (Previously 365.2425 — Gregorian — which drifts a few days
# over multi-decade dashas relative to standard almanacs.)
YEAR_DAYS = 365.25


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
    first_end = cur_start + dt.timedelta(days=balance_years * YEAR_DAYS)
    out.append({"lord": cycle[0], "start": cur_start, "end": first_end, "years": balance_years})

    cur_start = first_end
    for i in range(1, 9):
        lord_i = cycle[i % 9]
        yrs = years_map[lord_i]
        cur_end = cur_start + dt.timedelta(days=yrs * YEAR_DAYS)
        out.append({"lord": lord_i, "start": cur_start, "end": cur_end, "years": float(yrs)})
        cur_start = cur_end

    return out[:10]


def antardasha_for_segment(md_lord: str, md_start: dt.datetime, md_end: dt.datetime) -> List[Dict]:
    """Classical Vimshottari antardashas for a mahadasha segment.

    FIDELITY FIX (2026-07-19, see JYOTISH_FIDELITY_AUDIT_2026-07-19.md):
    For a BALANCE segment — a birth partway through a mahadasha — the
    antardasha cycle is entered MID-WAY: the antardashas before birth are
    already elapsed, and the remaining ones run at their FULL classical
    lengths (BPHS, Vimshottari-dasha adhyaya). The previous implementation
    rescaled all nine antardashas proportionally into the balance period,
    which is not the classical rule.

    Implementation (call-site compatible — same signature, same dict shape):
    anchor the notional full-mahadasha start at (md_end − full_period), lay
    out all nine antardashas at full length from that anchor, keep only the
    portion overlapping [md_start, md_end], clipping the first. For a
    full-length mahadasha segment this reproduces the standard complete
    table; for a balance segment it yields the classical mid-cycle entry.
    """
    order = [x[0] for x in DASHA_SEQUENCE]
    years_map = {k: y for k, y in DASHA_SEQUENCE}
    start_idx = order.index(md_lord)
    cycle = order[start_idx:] + order[:start_idx]

    full_years = float(years_map[md_lord])
    notional_start = md_end - dt.timedelta(days=full_years * YEAR_DAYS)

    out = []
    cur = notional_start
    for lord in cycle:
        dur_days = full_years * (years_map[lord] / 120.0) * YEAR_DAYS
        end = cur + dt.timedelta(days=dur_days)
        if end > md_start:  # antardasha not fully elapsed before segment start
            seg_start = max(cur, md_start)
            out.append({
                "lord": lord,
                "start": seg_start,
                "end": end,
                "days": (end - seg_start).total_seconds() / 86400.0,
            })
        cur = end
    return out
