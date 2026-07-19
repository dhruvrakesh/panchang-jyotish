import streamlit as st

# BUG-01 FIX: set_page_config must be the very first Streamlit call.
st.set_page_config(page_title="Jyotish Panchang & Horoscope", page_icon="🪔", layout="wide")

import datetime as dt
import json
import os

import pandas as pd
import pytz
from dotenv import load_dotenv
from openai import OpenAI

from jyotish import astro, panchang, dasha
from jyotish.utils import geocode_place, tz_from_latlon, coerce_tz
from jyotish.flags import compute_planet_flags, bhava_lordship_block
from jyotish.aspects import geo_aspects, drishti_rows
from jyotish.chart import draw_north_chart
from jyotish.ai_prompt import build_user_context, run_analysis
from jyotish.pdf_export import build_pdf_bytes

# ── Session state ──────────────────────────────────────────────────────────────
if "analysis_text" not in st.session_state:
    st.session_state["analysis_text"] = ""
if "saved_inputs" not in st.session_state:
    st.session_state["saved_inputs"] = None

load_dotenv()
_openai_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")
client = OpenAI(api_key=_openai_key) if _openai_key else None

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("🪔 Jyotish Panchang & Horoscope (Advanced v11)")
st.caption("Sidereal calculations via Swiss Ephemeris with configurable ayanāṃśa, house systems, nodes, and richer flags.")

# ── Birth form ─────────────────────────────────────────────────────────────────
with st.form("birth_form"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name (optional)", value="")
        dob = st.date_input("Date of Birth", value=dt.date(1990, 1, 1),
                            min_value=dt.date(1800, 1, 1), max_value=dt.date.today())
        tob = st.time_input("Time of Birth (local)")
    with col2:
        place = st.text_input("Place of Birth (City, Country)", value="Delhi, India")
        manual = st.checkbox("Manual lat/lon & timezone override")
        lat = lon = tzname = None
        if not manual:
            st.caption("We'll attempt to geocode the place and find timezone automatically.")
        else:
            lat    = st.number_input("Latitude (°, +N / -S)", value=28.6139, format="%.6f")
            lon    = st.number_input("Longitude (°, +E / -W)", value=77.2090, format="%.6f")
            tzname = st.selectbox("Timezone", options=pytz.all_timezones,
                                  index=pytz.all_timezones.index("Asia/Kolkata"))
    st.markdown("**Advanced settings**")
    adv1, adv2, adv3 = st.columns(3)
    with adv1:
        ayan_choice  = st.selectbox("Ayanāṃśa",
                                    options=["Lahiri", "Krishnamurti", "Raman", "Fagan/Bradley"], index=0)
    with adv2:
        node_choice  = st.selectbox("Node type", options=["True node", "Mean node"], index=1)
    with adv3:
        house_choice = st.selectbox("House system",
                                    options=["Whole Sign", "Sripati (Porphyry)", "Placidus"], index=0)
    submitted = st.form_submit_button("Compute Horoscope ✨")

if not submitted and not st.session_state.get("saved_inputs"):
    st.stop()

# ── Resolve / restore inputs ───────────────────────────────────────────────────
tzinfo = None
if submitted:
    if not manual:
        g = geocode_place(place) or (None, None)
        if g[0] is None:
            st.warning("Could not geocode the place. Please use manual override.")
            st.stop()
        lat, lon = g
        tzname = tz_from_latlon(lat, lon)
        if not tzname:
            st.warning("Could not determine timezone. Please use manual override.")
            st.stop()
    tzinfo = coerce_tz(tzname)
    if tzinfo is None:
        st.error("Invalid timezone.")
        st.stop()
    st.session_state["saved_inputs"] = {
        "name": name, "dob": dob, "tob": tob, "place": place,
        "lat": float(lat), "lon": float(lon), "tzname": tzname,
        "ayan": ayan_choice, "node": node_choice, "house": house_choice,
    }
else:
    s = st.session_state["saved_inputs"]
    name, dob, tob, place = s["name"], s["dob"], s["tob"], s["place"]
    lat, lon, tzname      = s["lat"], s["lon"], s["tzname"]
    ayan_choice, node_choice, house_choice = s["ayan"], s["node"], s["house"]
    tzinfo = coerce_tz(tzname)
    if tzinfo is None:
        st.error("Invalid timezone (from saved session). Use manual override to correct.")
        st.stop()

# ── Compute ────────────────────────────────────────────────────────────────────
birth_dt_local = tzinfo.localize(dt.datetime.combine(dob, tob))
weekday_name   = birth_dt_local.strftime("%A")
jd_ut          = astro.to_julday_ut(birth_dt_local, tzinfo)

astro.set_sidereal_mode(ayan_choice)
ayan    = astro.get_ayanamsa(jd_ut)
asc     = astro.ascendant_sidereal(jd_ut, lat, lon, ayan_choice)
planets = astro.all_planets_sidereal(jd_ut, ayan_choice, node_choice)

sun_lon  = planets["Sun"]["lon"]
moon_lon = planets["Moon"]["lon"]

t_num, paksha, t_name   = panchang.tithi(sun_lon, moon_lon)
nk_idx, nk_name, nk_pada = panchang.nakshatra(moon_lon)
yoga_idx, yoga_name       = panchang.yoga(sun_lon, moon_lon)
kar_idx, kar_name         = panchang.karana(sun_lon, moon_lon)

try:
    sr, ss = astro.sunrise_sunset_local(dob, lat, lon, tzinfo)
except Exception:
    sr = ss = None

asc_rashi  = panchang.rashi_name(asc)
moon_rashi = panchang.rashi_name(moon_lon)
sun_rashi  = panchang.rashi_name(sun_lon)

cusps_sid = astro.houses_sidereal(jd_ut, lat, lon, ayan_choice, house_choice)


def _planet_house(lon_):
    if house_choice == "Whole Sign":
        return astro.which_house_whole_sign(asc, lon_)
    return astro.which_house_from_cusps(lon_, cusps_sid)


planet_houses   = {k: _planet_house(v["lon"]) for k, v in planets.items()}
planet_flags    = compute_planet_flags(planets, sun_lon, panchang)
lordship_block  = bhava_lordship_block(asc, planet_houses, planets, panchang)
aspects_geo     = geo_aspects(planets)
aspects_drishti = drishti_rows(planets, panchang)

timeline  = dasha.vimshottari_from_birth(moon_lon, birth_dt_local, tzinfo)
dash_rows = [{
    "Mahadasha Lord": seg["lord"],
    "Start (local)":  seg["start"].strftime("%Y-%m-%d"),
    "End (local)":    seg["end"].strftime("%Y-%m-%d"),
    "Years":          round(seg["years"], 2),
} for seg in timeline]

# ── Birth Details ──────────────────────────────────────────────────────────────
st.subheader("Birth Details")
colA, colB, colC, colD = st.columns(4)
colA.metric("Date",           dob.strftime("%d %b %Y"))
colB.metric("Time (local)",   tob.strftime("%H:%M"))
colC.metric("Latitude",       f"{lat:.4f}°")
colD.metric("Longitude",      f"{lon:.4f}°")
st.caption(
    f"Timezone: **{tzname}**  •  Ayanāṃśa: **{ayan:.4f}° ({ayan_choice})**  •  "
    f"Weekday: **{weekday_name}**  •  Node: **{node_choice}**  •  Houses: **{house_choice}**"
)
if sr and ss:
    st.caption(f"Sunrise: **{sr.strftime('%H:%M')}**  •  Sunset: **{ss.strftime('%H:%M')}** (local)")

# ── Panchang ───────────────────────────────────────────────────────────────────
st.subheader("Panchang")
col1, col2 = st.columns(2)
with col1:
    st.metric("Paksha",       paksha)
    st.metric("Tithi (1–30)", f"{t_num} — {t_name}")
    st.metric("Yoga (1–27)",  f"{yoga_idx} — {yoga_name}")
with col2:
    st.metric("Nakshatra (1–27)", f"{nk_idx} — {nk_name} (Pada {nk_pada})")
    st.metric("Karana (1–60)",    f"{kar_idx} — {kar_name}")

# ── Ascendant & Luminaries ─────────────────────────────────────────────────────
st.subheader("Ascendant & Luminaries")
col6, col7, col8 = st.columns(3)
col6.metric("Ascendant (Lagna)", asc_rashi)
col7.metric("Moon Rāśi",         moon_rashi)
col8.metric("Sun Rāśi",          sun_rashi)

# ── Planetary Positions ────────────────────────────────────────────────────────
st.subheader("Sidereal Planetary Positions")
rows = []
for nm, data in planets.items():
    lonv = data["lon"] % 360.0
    rows.append({
        "Body":          nm,
        "Longitude (°)": round(lonv, 4),
        "Rāśi":          panchang.rashi_name(lonv),
        "Deg in Rāśi":   round(lonv % 30.0, 2),
        "Speed (°/day)": round(data["speed"], 4),
    })
df_plan = pd.DataFrame(rows).set_index("Body")
st.dataframe(df_plan, use_container_width=True)

df_more = pd.DataFrame([{
    "Body":              nm,
    "Rāśi":              panchang.rashi_name(planets[nm]["lon"]),
    "House":             planet_houses[nm],
    "Retro/Comb/Status": planet_flags[nm],
} for nm in planets]).set_index("Body")
st.dataframe(df_more, use_container_width=True)

# ── Aspects ────────────────────────────────────────────────────────────────────
st.subheader("Aspects")
show_western = st.toggle("Show Western aspects (geometric/orb-based)", value=False,
                          help="Ptolemaic aspects with degree orbs")
st.session_state["show_western"] = show_western
if show_western:
    st.markdown("**Geometric aspects (Ptolemaic, ±orbs)**")
    st.dataframe(
        pd.DataFrame(aspects_geo) if aspects_geo
        else pd.DataFrame([], columns=["A", "B", "type", "delta"]),
        use_container_width=True,
    )
st.markdown("**Parāśari graha-dṛṣṭi (classical)**")
st.dataframe(
    pd.DataFrame(aspects_drishti) if aspects_drishti
    else pd.DataFrame([], columns=["A", "B", "type"]),
    use_container_width=True,
)

# ── Chart ──────────────────────────────────────────────────────────────────────
st.subheader("Chart (North-Indian — de-overlapped)")
st.pyplot(draw_north_chart(asc, planets, show_degrees=True))

# ── Vimshottari Dasha ──────────────────────────────────────────────────────────
st.subheader("Vimshottari Mahadasha")
st.dataframe(pd.DataFrame(dash_rows), use_container_width=True)
with st.expander("Antardaśā (Sub-periods)", expanded=False):
    md_options = [
        f"{i+1}. {r['Mahadasha Lord']} ({r['Start (local)']}→{r['End (local)']})"
        for i, r in enumerate(dash_rows)
    ]
    sel     = st.selectbox("Mahadasha to expand", options=md_options, index=0)
    sel_row = dash_rows[md_options.index(sel)]
    antar   = dasha.antardasha_for_segment(
        sel_row["Mahadasha Lord"],
        dt.datetime.strptime(sel_row["Start (local)"], "%Y-%m-%d"),
        dt.datetime.strptime(sel_row["End (local)"],   "%Y-%m-%d"),
    )
    st.dataframe(pd.DataFrame([{
        "Antar Lord": a["lord"],
        "Start":      a["start"].strftime("%Y-%m-%d"),
        "End":        a["end"].strftime("%Y-%m-%d"),
        "Days":       round(a["days"], 1),
    } for a in antar]), use_container_width=True)

# ── Full Text Summary ──────────────────────────────────────────────────────────
with st.expander("Full Text Summary", expanded=True):
    for label, val in [
        ("Paksha",             paksha),
        ("Tithi",              f"{t_num} — {t_name}"),
        ("Nakshatra",          f"{nk_idx} — {nk_name} (Pada {nk_pada})"),
        ("Yoga",               f"{yoga_idx} — {yoga_name}"),
        ("Karana",             f"{kar_idx} — {kar_name}"),
        ("Ascendant (Lagna)",  asc_rashi),
        ("Moon Rāśi",          moon_rashi),
        ("Sun Rāśi",           sun_rashi),
    ]:
        st.write(f"**{label}:** {val}")

# ── AI Analysis ────────────────────────────────────────────────────────────────
st.subheader("Vedic Jyotish Analysis")
analysis_model = st.selectbox("Model", options=["gpt-4o-mini", "gpt-4o"],
                               index=0, key="ai_model_sel")
analysis_style = st.selectbox("Tone",
                               options=["Classical (traditional)", "Clear & businesslike"],
                               index=0, key="ai_tone_sel")

if st.button("Generate 300–500 word Analysis", key="ai_generate_btn"):
    if client is None:
        st.warning("No OpenAI key found. Add OPENAI_API_KEY or OPENAI_KEY to your .env, then restart.")
    else:
        _jup_7_moon = (
            int((planets["Jupiter"]["lon"] % 360) // 30)
            - int((planets["Moon"]["lon"] % 360) // 30)
        ) % 12 == 6
        user_ctx = build_user_context(
            name=name, place=place, tzinfo=tzinfo,
            birth_dt_local=birth_dt_local, weekday_name=weekday_name,
            ayan_choice=ayan_choice, ayan=ayan,
            node_choice=node_choice, house_choice=house_choice,
            asc_rashi=asc_rashi, moon_rashi=moon_rashi, sun_rashi=sun_rashi,
            paksha=paksha, t_num=t_num, t_name=t_name,
            nk_idx=nk_idx, nk_name=nk_name, nk_pada=nk_pada,
            yoga_idx=yoga_idx, yoga_name=yoga_name,
            kar_idx=kar_idx, kar_name=kar_name,
            planets=planets, planet_houses=planet_houses,
            planet_flags=planet_flags, lordship_block=lordship_block,
            aspects_geo=aspects_geo, dash_rows=dash_rows,
            jup_7_to_moon=_jup_7_moon, panchang_module=panchang,
        )
        try:
            with st.spinner("Generating analysis…"):
                st.session_state["analysis_text"] = run_analysis(
                    client, analysis_model, analysis_style, user_ctx
                )
            st.success("Analysis generated below.")
        except Exception as e:
            st.exception(e)

if st.session_state.get("analysis_text"):
    st.markdown(st.session_state["analysis_text"])
    st.download_button("Download analysis.txt",
                       data=st.session_state["analysis_text"],
                       file_name="jyotish_analysis.txt")

# ── Downloads ──────────────────────────────────────────────────────────────────
st.subheader("Downloads")
out_json = {
    "name": name, "place": place, "lat": lat, "lon": lon,
    "timezone": tzinfo.zone,
    "birth_datetime_local": birth_dt_local.isoformat(),
    "ayanamsa_deg": float(ayan), "ayanamsa_name": ayan_choice,
    "node_type": node_choice, "house_system": house_choice,
    "asc_deg": float(asc), "asc_rashi": str(asc_rashi),
    "panchang": {
        "paksha": paksha,
        "tithi_number": int(t_num), "tithi_name": t_name,
        "nakshatra_index": int(nk_idx), "nakshatra_name": nk_name,
        "nakshatra_pada": int(nk_pada),
        "yoga_index": int(yoga_idx), "yoga_name": yoga_name,
        "karana_index": int(kar_idx), "karana_name": kar_name,
    },
    "planets": {
        k: {"lon": float(v["lon"]), "speed": float(v["speed"]),
             "house": planet_houses[k], "flags": planet_flags[k]}
        for k, v in planets.items()
    },
    "sunrise_local": sr.isoformat() if hasattr(sr, "isoformat") else None,
    "sunset_local":  ss.isoformat() if hasattr(ss, "isoformat") else None,
    "dasha": dash_rows,
}
st.download_button("Download JSON Report",
                   data=json.dumps(out_json, indent=2),
                   file_name="horoscope.json", mime="application/json")
st.download_button("Download Dasha CSV",
                   data=pd.DataFrame(dash_rows).to_csv(index=False),
                   file_name="vimshottari.csv", mime="text/csv")

pdf_bytes = build_pdf_bytes(
    name=name, place=place, tzname=tzname,
    birth_dt_local=birth_dt_local, weekday_name=weekday_name,
    lat=float(lat), lon=float(lon),
    ayan_choice=ayan_choice, ayan=float(ayan),
    node_choice=node_choice, house_choice=house_choice,
    asc=asc, planets=planets,
    paksha=paksha, t_num=t_num, t_name=t_name,
    nk_idx=nk_idx, nk_name=nk_name, nk_pada=nk_pada,
    yoga_idx=yoga_idx, yoga_name=yoga_name,
    kar_idx=kar_idx, kar_name=kar_name,
    df_plan=df_plan,
    aspects_geo=aspects_geo, aspects_drishti=aspects_drishti,
    timeline=timeline, dash_rows=dash_rows,
    analysis_text=st.session_state.get("analysis_text", ""),
    show_western_aspects=bool(st.session_state.get("show_western", False)),
)
st.download_button("Download PDF Report",
                   data=pdf_bytes,
                   file_name="horoscope_report.pdf", mime="application/pdf")
st.caption("© 2025 — Educational purposes only. Astrology calculations may vary by tradition and parameters.")
