# Regression test for the 2026-07-19 antardasha fidelity fix.
# Chart: the independently verified reference horoscope (Moon 217.8270° sidereal,
# Anuradha pada 2 -> Saturn mahadasha, balance 12.596y of 19y).
# Classical rule (BPHS): birth 6.40y into Saturn mahadasha falls in the
# Saturn/KETU antardasha (Sat 3.008 + Merc 2.692 = 5.70 < 6.40 < 6.81), with
# Ketu partially elapsed; subsequent antardashas run at FULL length.

import datetime as dt
import pytz

from jyotish.dasha import vimshottari_from_birth, antardasha_for_segment, YEAR_DAYS

TZ = pytz.timezone("Asia/Kolkata")
BIRTH = TZ.localize(dt.datetime(1988, 8, 21, 4, 15))
MOON_LON = 217.8270  # sidereal, Lahiri


def test_balance_mahadasha_is_saturn_12_6y():
    rows = vimshottari_from_birth(MOON_LON, BIRTH, TZ)
    assert rows[0]["lord"] == "Saturn"
    assert abs(rows[0]["years"] - 12.596) < 0.02


def test_balance_antardasha_enters_mid_cycle_at_ketu():
    rows = vimshottari_from_birth(MOON_LON, BIRTH, TZ)
    md = rows[0]
    antars = antardasha_for_segment(md["lord"], md["start"], md["end"])

    # Birth falls in Saturn/Ketu: Sat/Sat and Sat/Merc are already elapsed.
    assert antars[0]["lord"] == "Ketu", (
        f"first antardasha at birth must be Ketu (mid-cycle entry), got {antars[0]['lord']}"
    )
    # Remaining Ketu portion ~0.405y ≈ 148 days (clipped at birth).
    assert abs(antars[0]["days"] - 0.4047 * YEAR_DAYS) < 3.0

    # Next antardasha, Saturn/Venus, runs at FULL classical length: 19*20/120 y.
    assert antars[1]["lord"] == "Venus"
    full_venus_days = 19 * (20 / 120.0) * YEAR_DAYS
    assert abs(antars[1]["days"] - full_venus_days) < 1.0

    # The antardashas must tile the segment: last end == mahadasha end (±1 day).
    assert abs((antars[-1]["end"] - md["end"]).total_seconds()) < 86400.0


def test_full_mahadasha_antardashas_unchanged():
    rows = vimshottari_from_birth(MOON_LON, BIRTH, TZ)
    md = rows[1]  # Mercury mahadasha — full 17y segment
    antars = antardasha_for_segment(md["lord"], md["start"], md["end"])
    assert len(antars) == 9
    assert antars[0]["lord"] == "Mercury"
    # Mercury/Mercury = 17*17/120 years, at full length.
    assert abs(antars[0]["days"] - 17 * (17 / 120.0) * YEAR_DAYS) < 1.0
