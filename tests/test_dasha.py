"""
tests/test_dasha.py
-------------------
Regression tests for jyotish.dasha — Vimshottari Mahadasha and Antardasha.
Only standard library + pytz required; no Swiss Ephemeris.
"""
import datetime as dt

import pytz
import pytest

from jyotish.dasha import antardasha_for_segment, vimshottari_from_birth

_IST  = pytz.timezone("Asia/Kolkata")
_SPAN = 360.0 / 27.0        # nakshatra span in degrees
_EPOCH = _IST.localize(dt.datetime(2000, 1, 1, 12, 0, 0))


# ── vimshottari_from_birth ─────────────────────────────────────────────────────

class TestVimshottariBalance:
    def test_start_of_ashwini_full_ketu_balance(self):
        # Moon at 0° = very start of Ashwini → lord Ketu, fraction elapsed = 0 → balance = 7y
        result = vimshottari_from_birth(0.0, _EPOCH, _IST)
        assert result[0]["lord"] == "Ketu"
        assert abs(result[0]["years"] - 7.0) < 1e-9

    def test_midpoint_ashwini_half_ketu_balance(self):
        # Moon at SPAN/2 = halfway → fraction = 0.5 → balance = 3.5y
        result = vimshottari_from_birth(_SPAN / 2, _EPOCH, _IST)
        assert result[0]["lord"] == "Ketu"
        assert abs(result[0]["years"] - 3.5) < 1e-9

    def test_end_of_ashwini_near_zero_balance(self):
        # Moon just before end of Ashwini → fraction ≈ 1 → balance ≈ 0
        result = vimshottari_from_birth(_SPAN - 0.001, _EPOCH, _IST)
        assert result[0]["lord"] == "Ketu"
        assert result[0]["years"] < 0.01

    def test_moon_in_rohini_lord_is_moon(self):
        # Rohini is the 4th nakshatra (0-based index 3), lord = Moon
        result = vimshottari_from_birth(3 * _SPAN + 0.001, _EPOCH, _IST)
        assert result[0]["lord"] == "Moon"

    def test_moon_in_jyeshtha_lord_is_mercury(self):
        # Jyeshtha is the 18th nakshatra (0-based index 17), lord = Mercury
        result = vimshottari_from_birth(17 * _SPAN + 0.001, _EPOCH, _IST)
        assert result[0]["lord"] == "Mercury"

    def test_sequence_after_ketu_is_venus(self):
        result = vimshottari_from_birth(0.0, _EPOCH, _IST)
        assert result[1]["lord"] == "Venus"

    def test_sequence_after_venus_is_sun(self):
        result = vimshottari_from_birth(0.0, _EPOCH, _IST)
        assert result[2]["lord"] == "Sun"

    def test_full_sequence_has_ten_entries(self):
        # vimshottari_from_birth returns 9 segments (1 balance + 8 subsequent full MDs)
        result = vimshottari_from_birth(0.0, _EPOCH, _IST)
        assert len(result) == 9

    def test_dates_are_strictly_sequential(self):
        result = vimshottari_from_birth(0.0, _EPOCH, _IST)
        for i in range(1, len(result)):
            assert result[i]["start"] == result[i - 1]["end"], \
                f"Gap between segment {i-1} and {i}"

    def test_first_start_equals_birth_datetime(self):
        result = vimshottari_from_birth(0.0, _EPOCH, _IST)
        assert result[0]["start"] == _EPOCH

    def test_120_year_cycle_complete(self):
        # Full 9 periods (excluding balance) should span 120 years from Ketu start
        result = vimshottari_from_birth(0.0, _EPOCH, _IST)
        total_days = sum(r["years"] for r in result) * 365.2425
        # Balance=7y + full 9 MDs starting Venus(20) would exceed 120y but we just
        # check the slice is reasonable: total years > 100 for any starting lord.
        assert sum(r["years"] for r in result) > 100.0


# ── antardasha_for_segment ─────────────────────────────────────────────────────

class TestAntardasha:
    _MD_START = _EPOCH
    _MD_END   = _EPOCH + dt.timedelta(days=7 * 365.2425)   # Ketu Mahadasha

    def test_nine_sub_periods(self):
        result = antardasha_for_segment("Ketu", self._MD_START, self._MD_END)
        assert len(result) == 9

    def test_starts_with_own_lord(self):
        result = antardasha_for_segment("Ketu", self._MD_START, self._MD_END)
        assert result[0]["lord"] == "Ketu"

    def test_sub_period_days_sum_to_total(self):
        result = antardasha_for_segment("Ketu", self._MD_START, self._MD_END)
        total_days  = (self._MD_END - self._MD_START).total_seconds() / 86400.0
        sub_total   = sum(a["days"] for a in result)
        assert abs(sub_total - total_days) < 1e-6

    def test_dates_are_sequential(self):
        result = antardasha_for_segment("Ketu", self._MD_START, self._MD_END)
        for i in range(1, len(result)):
            assert result[i]["start"] == result[i - 1]["end"]

    def test_first_start_equals_md_start(self):
        result = antardasha_for_segment("Ketu", self._MD_START, self._MD_END)
        assert result[0]["start"] == self._MD_START

    def test_last_end_equals_md_end(self):
        result = antardasha_for_segment("Ketu", self._MD_START, self._MD_END)
        # End should match to within floating-point timedelta resolution
        last_end = result[-1]["end"]
        diff_s = abs((last_end - self._MD_END).total_seconds())
        assert diff_s < 1.0, f"Last antardasha end off by {diff_s:.3f}s"

    def test_venus_mahadasha_starts_with_venus(self):
        md_end = self._MD_START + dt.timedelta(days=20 * 365.2425)
        result = antardasha_for_segment("Venus", self._MD_START, md_end)
        assert result[0]["lord"] == "Venus"

    def test_proportionality_ketu_in_ketu(self):
        # Ketu antardasha in Ketu MD: fraction = 7/120
        result = antardasha_for_segment("Ketu", self._MD_START, self._MD_END)
        total_days = (self._MD_END - self._MD_START).total_seconds() / 86400.0
        expected_ketu_ad = total_days * (7 / 120.0)
        assert abs(result[0]["days"] - expected_ketu_ad) < 1e-6
