"""
tests/test_panchang.py
----------------------
Regression tests for jyotish.panchang — pure arithmetic, no ephemeris needed.
All expected values derived from classical Panchanga rules and verified manually.
"""
import pytest
from jyotish.panchang import tithi, nakshatra, yoga, karana, rashi_name

_SPAN = 360.0 / 27.0  # degrees per nakshatra (≈ 13.333°)


# ── tithi ──────────────────────────────────────────────────────────────────────

class TestTithi:
    def test_shukla_pratipada(self):
        t, pak, name = tithi(0.0, 6.0)   # diff = 6°, idx = 0 → tithi 1
        assert t == 1
        assert pak == "Shukla"
        assert name == "Pratipada"

    def test_shukla_dvitiya(self):
        t, pak, name = tithi(0.0, 12.0)  # diff = 12°, idx = 1 → tithi 2
        assert t == 2
        assert pak == "Shukla"
        assert name == "Dvitiya"

    def test_purnima(self):
        t, pak, name = tithi(0.0, 168.0)  # diff = 168° = 14*12 → tithi 15
        assert t == 15
        assert pak == "Shukla"
        assert name == "Purnima"

    def test_krishna_pratipada(self):
        t, pak, name = tithi(0.0, 180.0)  # diff = 180° → tithi 16 = Krishna Pratipada
        assert t == 16
        assert pak == "Krishna"
        assert name == "Pratipada"

    def test_amavasya(self):
        t, pak, name = tithi(0.0, 348.0)  # diff = 348° = 29*12 → tithi 30
        assert t == 30
        assert pak == "Krishna"
        assert name == "Amavasya"

    def test_wraparound_moon_behind_sun(self):
        # moon_lon < sun_lon — normalize must handle the wrap correctly
        t, pak, name = tithi(350.0, 6.0)  # diff = (6-350)%360 = 16° → tithi 2
        assert t == 2
        assert pak == "Shukla"
        assert name == "Dvitiya"

    def test_all_tithis_have_valid_number(self):
        for i in range(30):
            moon_lon = i * 12.0 + 6.0  # midpoint of each tithi window
            t, pak, name = tithi(0.0, moon_lon)
            assert 1 <= t <= 30
            assert pak in ("Shukla", "Krishna")
            assert isinstance(name, str) and len(name) > 0


# ── nakshatra ──────────────────────────────────────────────────────────────────

class TestNakshatra:
    def test_ashwini_pada_1(self):
        idx, name, pada = nakshatra(0.0)
        assert idx == 1
        assert name == "Ashwini"
        assert pada == 1

    def test_ashwini_pada_3(self):
        # Half of Ashwini span ≈ 6.667° → pada 3
        idx, name, pada = nakshatra(_SPAN / 2)
        assert idx == 1
        assert name == "Ashwini"
        assert pada == 3

    def test_bharani(self):
        idx, name, pada = nakshatra(_SPAN + 0.001)
        assert idx == 2
        assert name == "Bharani"

    def test_revati_last_nakshatra(self):
        idx, name, pada = nakshatra(360.0 - 0.001)
        assert idx == 27
        assert name == "Revati"

    def test_wraparound_beyond_360(self):
        idx, name, pada = nakshatra(360.0 + 5.0)
        assert idx == 1
        assert name == "Ashwini"

    def test_pada_range(self):
        # Each nakshatra has exactly 4 padas
        for nk in range(27):
            for pada_n in range(1, 5):
                lon = nk * _SPAN + (pada_n - 0.5) * (_SPAN / 4)
                idx, name, pada = nakshatra(lon)
                assert pada == pada_n, f"nk={nk}, expected pada {pada_n}, got {pada}"


# ── yoga ───────────────────────────────────────────────────────────────────────

class TestYoga:
    def test_vishkumbha(self):
        idx, name = yoga(0.0, 0.0)   # sum = 0
        assert idx == 1
        assert name == "Vishkumbha"

    def test_preeti(self):
        idx, name = yoga(0.0, _SPAN + 0.001)  # sum just past one span → Yoga 2
        assert idx == 2
        assert name == "Preeti"

    def test_sum_wraparound(self):
        # sum = 360 → 0 → back to Vishkumbha
        idx, name = yoga(180.0, 180.0)
        assert idx == 1
        assert name == "Vishkumbha"

    def test_vaidhriti(self):
        # Vaidhriti is the 27th and last Yoga; sum ≥ 26*span
        idx, name = yoga(0.0, 26 * _SPAN + 0.001)
        assert idx == 27
        assert name == "Vaidhriti"

    def test_all_yogas_covered(self):
        seen = set()
        for i in range(27):
            idx, name = yoga(0.0, i * _SPAN + 0.1)
            seen.add(idx)
        assert len(seen) == 27


# ── karana ─────────────────────────────────────────────────────────────────────

class TestKarana:
    def test_slot_1_kimstughna(self):
        num, name = karana(0.0, 3.0)    # diff=3, idx0=0
        assert num == 1
        assert name == "Kimstughna"

    def test_slot_2_bava(self):
        num, name = karana(0.0, 6.0)    # diff=6, idx0=1
        assert num == 2
        assert name == "Bava"

    def test_slot_3_balava(self):
        num, name = karana(0.0, 12.0)   # diff=12, idx0=2
        assert num == 3
        assert name == "Balava"

    def test_movable_cycling_slot_8_vishti(self):
        # idx0=7 → (7-1)%7=6 → KARANAS_MOVABLE[6]="Vishti (Bhadra)"
        num, name = karana(0.0, 42.0)   # diff=42, idx0=7
        assert num == 8
        assert name == "Vishti (Bhadra)"

    def test_slot_58_shakuni(self):
        num, name = karana(0.0, 342.0)  # diff=342, idx0=57
        assert num == 58
        assert name == "Shakuni"

    def test_slot_59_chatushpada(self):
        num, name = karana(0.0, 348.0)  # diff=348, idx0=58
        assert num == 59
        assert name == "Chatushpada"

    def test_slot_60_naga_bug03_regression(self):
        """BUG-03 regression: second half of Amavasya must yield Naga, not an IndexError or wrong name."""
        num, name = karana(0.0, 354.0)  # diff=354, idx0=59
        assert num == 60
        assert name == "Naga"

    def test_all_60_slots_reachable(self):
        seen_nums = set()
        for i in range(60):
            diff = i * 6.0 + 3.0  # midpoint of each slot
            num, name = karana(0.0, diff)
            seen_nums.add(num)
            assert isinstance(name, str) and len(name) > 0
        assert seen_nums == set(range(1, 61))


# ── rashi_name ─────────────────────────────────────────────────────────────────

class TestRashiName:
    def test_aries(self):
        assert rashi_name(0.0) == "Mesha (Aries)"

    def test_taurus(self):
        assert rashi_name(30.0) == "Vrishabha (Taurus)"

    def test_gemini(self):
        assert rashi_name(60.0) == "Mithuna (Gemini)"

    def test_scorpio_at_210(self):
        assert rashi_name(210.0) == "Vrishchika (Scorpio)"

    def test_pisces_near_360(self):
        assert rashi_name(359.9) == "Meena (Pisces)"

    def test_wraparound_360(self):
        assert rashi_name(360.0) == "Mesha (Aries)"

    def test_all_12_rashis_covered(self):
        from jyotish.panchang import RASHIS
        seen = set()
        for i in range(12):
            seen.add(rashi_name(i * 30.0 + 15.0))
        assert len(seen) == 12
        assert seen == set(RASHIS)
