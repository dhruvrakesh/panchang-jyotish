"""
tests/test_astro.py
-------------------
Tests for jyotish.astro — split into two classes:
  1. Pure-Python helpers (no Swiss Ephemeris): always run.
  2. Ephemeris-dependent functions: skipped if pyswisseph is not installed.
"""
import datetime as dt

import pytz
import pytest

# Pure-Python helpers — importable without swisseph
from jyotish.astro import which_house_whole_sign, which_house_from_cusps

_IST = pytz.timezone("Asia/Kolkata")


# ── which_house_whole_sign (pure arithmetic) ───────────────────────────────────

class TestWholeSignHouse:
    def test_asc_aries_planet_in_aries_is_h1(self):
        assert which_house_whole_sign(0.0, 15.0) == 1

    def test_asc_aries_planet_in_taurus_is_h2(self):
        assert which_house_whole_sign(0.0, 45.0) == 2

    def test_asc_aries_planet_in_pisces_is_h12(self):
        assert which_house_whole_sign(0.0, 345.0) == 12

    def test_asc_taurus_planet_in_aries_is_h12(self):
        # Taurus = H1; Aries is the 12th sign from Taurus
        assert which_house_whole_sign(30.0, 15.0) == 12

    def test_asc_gemini_planet_in_scorpio_is_h6(self):
        # Gemini(idx=2), Scorpio(idx=7): (7-2)%12+1 = 6
        assert which_house_whole_sign(60.0, 225.0) == 6

    def test_same_sign_as_asc_is_always_h1(self):
        for sign_idx in range(12):
            asc_deg     = sign_idx * 30.0 + 15.0
            planet_deg  = sign_idx * 30.0 + 5.0
            assert which_house_whole_sign(asc_deg, planet_deg) == 1, \
                f"Expected H1 for sign_idx={sign_idx}"

    def test_opposite_sign_is_h7(self):
        for sign_idx in range(12):
            asc_deg    = sign_idx * 30.0 + 15.0
            opp_deg    = ((sign_idx + 6) % 12) * 30.0 + 15.0
            assert which_house_whole_sign(asc_deg, opp_deg) == 7


# ── which_house_from_cusps (pure arithmetic) ───────────────────────────────────

class TestWhichHouseFromCusps:
    # Uniform whole-sign cusps starting at Aries (0°) — simple to reason about
    _CUSPS = [i * 30.0 for i in range(12)]

    def test_planet_in_h1(self):
        assert which_house_from_cusps(15.0, self._CUSPS) == 1

    def test_planet_in_h2(self):
        assert which_house_from_cusps(45.0, self._CUSPS) == 2

    def test_planet_in_h12(self):
        assert which_house_from_cusps(350.0, self._CUSPS) == 12

    def test_planet_on_cusp_of_h2(self):
        # Exactly 30° → start of house 2
        assert which_house_from_cusps(30.0, self._CUSPS) == 2

    def test_all_twelve_houses_reachable(self):
        seen = set()
        for i in range(12):
            lon = i * 30.0 + 15.0   # midpoint of each sign
            seen.add(which_house_from_cusps(lon, self._CUSPS))
        assert seen == set(range(1, 13))


# ── Ephemeris-dependent tests ─────────────────────────────────────────────────

_swe = pytest.importorskip(
    "swisseph",
    reason="pyswisseph not installed — skipping ephemeris-dependent tests",
)

from jyotish.astro import to_julday_ut, set_sidereal_mode, get_ayanamsa  # noqa: E402


class TestJulianDay:
    def test_j2000_epoch(self):
        # J2000.0: 2000-Jan-1 12:00 UT = JD 2451545.0  (IAU standard)
        dt_utc = pytz.utc.localize(dt.datetime(2000, 1, 1, 12, 0, 0))
        jd = to_julday_ut(dt_utc, pytz.utc)
        assert abs(jd - 2451545.0) < 1e-4

    def test_result_is_positive(self):
        dt_local = _IST.localize(dt.datetime(1990, 6, 15, 12, 0))
        jd = to_julday_ut(dt_local, _IST)
        assert jd > 0

    def test_later_date_has_higher_jd(self):
        dt1 = _IST.localize(dt.datetime(1990, 1, 1, 12, 0))
        dt2 = _IST.localize(dt.datetime(2000, 1, 1, 12, 0))
        jd1 = to_julday_ut(dt1, _IST)
        jd2 = to_julday_ut(dt2, _IST)
        assert jd2 > jd1

    def test_one_day_apart(self):
        dt1 = pytz.utc.localize(dt.datetime(2000, 1, 1, 12, 0))
        dt2 = pytz.utc.localize(dt.datetime(2000, 1, 2, 12, 0))
        jd1 = to_julday_ut(dt1, pytz.utc)
        jd2 = to_julday_ut(dt2, pytz.utc)
        assert abs((jd2 - jd1) - 1.0) < 1e-6


class TestAyanamsa:
    def test_lahiri_ayanamsa_near_j2000_is_reasonable(self):
        # Lahiri ayanamsa ≈ 23.85° near J2000.0
        set_sidereal_mode("Lahiri")
        dt_utc = pytz.utc.localize(dt.datetime(2000, 1, 1, 12, 0))
        jd = to_julday_ut(dt_utc, pytz.utc)
        ayan = get_ayanamsa(jd)
        assert 22.0 < ayan < 25.0, f"Unexpected Lahiri ayanamsa: {ayan}"

    def test_different_ayanamsas_differ(self):
        dt_utc = pytz.utc.localize(dt.datetime(2000, 1, 1, 12, 0))
        jd = to_julday_ut(dt_utc, pytz.utc)
        set_sidereal_mode("Lahiri")
        ayan_lahiri = get_ayanamsa(jd)
        set_sidereal_mode("Fagan/Bradley")
        ayan_fb = get_ayanamsa(jd)
        assert ayan_lahiri != pytest.approx(ayan_fb, abs=0.01)
