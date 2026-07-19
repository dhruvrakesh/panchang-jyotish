import math
from typing import Tuple

RASHIS = [
    "Mesha (Aries)", "Vrishabha (Taurus)", "Mithuna (Gemini)", "Karka (Cancer)",
    "Simha (Leo)", "Kanya (Virgo)", "Tula (Libra)", "Vrishchika (Scorpio)",
    "Dhanu (Sagittarius)", "Makara (Capricorn)", "Kumbha (Aquarius)", "Meena (Pisces)"
]

TITHIS_15 = [
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dvadashi","Trayodashi","Chaturdashi","Purnima/Amavasya"
]

NAKSHATRAS = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira",
    "Ardra","Punarvasu","Pushya","Ashlesha","Magha",
    "Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati",
    "Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha",
    "Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada",
    "Uttara Bhadrapada","Revati"
]

YOGAS = [
    "Vishkumbha","Preeti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarma","Dhriti",
    "Shoola","Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra","Siddhi","Vyatipata",
    "Variyana","Parigha","Shiva","Siddha","Sadhya","Shubha","Shukla","Brahma","Indra","Vaidhriti"
]

KARANAS_MOVABLE = ["Bava","Balava","Kaulava","Taitila","Gara","Vanija","Vishti (Bhadra)"]
# Classical fixed Karanas at the end of the 60-Karana cycle (BPHS, Panchanga Adhyaya):
#   58th = Shakuni, 59th = Chatushpada, 60th = Naga.
# Note: Kimstughna is the 1st Karana (first half of Shukla Pratipada) and does NOT repeat at
# the end in the standard Parashari count.  The common alternate tradition that places a second
# Kimstughna as the 60th is noted but not implemented here; validate against your almanac.
KARANAS_FIXED_END = ["Shakuni", "Chatushpada", "Naga"]
KARANA_FIRST = "Kimstughna"

def normalize(x: float) -> float:
    return x % 360.0

def tithi(sun_lon: float, moon_lon: float):
    diff = normalize(moon_lon - sun_lon)
    t = int(diff // 12) + 1  # 1..30
    paksha = "Shukla" if t <= 15 else "Krishna"
    if t == 15:
        tname = "Purnima"
    elif t == 30:
        tname = "Amavasya"
    else:
        tname = TITHIS_15[(t-1) % 15]
    return t, paksha, tname

def nakshatra(moon_lon: float):
    span = 360.0 / 27.0
    idx0 = int(normalize(moon_lon) // span)
    pada = int(((normalize(moon_lon) % span) // (span/4))) + 1
    return idx0 + 1, NAKSHATRAS[idx0], pada

def yoga(sun_lon: float, moon_lon: float):
    span = 360.0 / 27.0
    s = normalize(sun_lon + moon_lon)
    idx0 = int(s // span)
    return idx0 + 1, YOGAS[idx0]

def karana(sun_lon: float, moon_lon: float):
    """Return (karana_number 1-60, karana_name) for the given sun/moon longitudes.

    Sequence (BPHS, Panchanga Adhyaya):
      Slot 1  : Kimstughna (fixed — first half of Shukla Pratipada)
      Slots 2–57 : 7 movable Karanas cycling 8 times = 56 slots
                   (Bava, Balava, Kaulava, Taitila, Gara, Vanija, Vishti)
      Slot 58 : Shakuni  (fixed)
      Slot 59 : Chatushpada (fixed)
      Slot 60 : Naga (fixed — second half of Krishna Amavasya)
    """
    diff = normalize(moon_lon - sun_lon)
    idx0 = int(diff // 6.0)  # 0-based index, range 0..59

    if idx0 == 0:
        # First half of Shukla Pratipada
        return 1, KARANA_FIRST                          # Kimstughna

    if 1 <= idx0 <= 56:
        # 7 movable Karanas repeating 8 times (slots 2–57, idx0 1–56)
        name = KARANAS_MOVABLE[(idx0 - 1) % 7]
        return idx0 + 1, name

    # Final 3 fixed Karanas (slots 58–60, idx0 57–59)
    if idx0 == 57:
        return 58, KARANAS_FIXED_END[0]  # Shakuni
    if idx0 == 58:
        return 59, KARANAS_FIXED_END[1]  # Chatushpada
    # idx0 == 59 → second half of Amavasya → Naga (BUG-03 FIX: previously wrong)
    return 60, KARANAS_FIXED_END[2]      # Naga

def rashi_name(lon: float) -> str:
    return RASHIS[int((normalize(lon)) // 30)]
