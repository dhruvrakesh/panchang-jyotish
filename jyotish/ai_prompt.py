"""
jyotish/ai_prompt.py
---------------------
OpenAI prompt assembly and API call for Vedic Jyotish analysis.

Provides:
  build_user_context(...)  -> str
  build_sys_prompt(style)  -> str
  run_analysis(client, model, style, context) -> str
"""
import logging
from typing import Optional

logger = logging.getLogger("jyotish.ai_prompt")


def build_sys_prompt(style: str) -> str:
    if style == "Clear & businesslike":
        return (
            "You are a careful, modern Jyotish analyst. Write a structured 300–500 word "
            "reading using ONLY the data provided. "
            "Always include bhava (house) for EVERY graha. "
            "Use the exact Mahadasha lines between the triple backticks verbatim. "
            "If 'JUPITER_7TH_TO_MOON' is True, explicitly write: "
            "'Jupiter casts full 7th drishti to the Moon (neecha-bhanga support).' "
            "Do not invent dates or placements. "
            "Sections: Overview; Panchanga & Temperament; Lagna & Chandra; "
            "Graha-by-Graha (with house); Aspects; Mahadasha (exact dates); Guidance. "
            "Avoid deterministic health/finance claims; keep it grounded in Vedic principles."
        )
    # Classical (traditional)
    return (
        "You are a Vedic Jyotish scholar. Compose a balanced, evidence-based 300–500 word reading. "
        "MANDATORY: State the bhava (house) for EVERY graha in a Graha-by-Graha section "
        "as 'Sun — sign, House N, deg, [flags]'. "
        "MANDATORY: Include a line: 'Jupiter casts full 7th drishti to the Moon "
        "(neecha-bhanga support).' IF AND ONLY IF JUPITER_7TH_TO_MOON is True. "
        "MANDATORY: In the Mahadasha section, reproduce EXACTLY the lines between the "
        "triple backticks, no paraphrase. "
        "Sections: Overview; Panchanga & Temperament; Lagna & Chandra; Graha-by-Graha; "
        "Aspects; Mahadasha (exact dates); Guidance."
    )


def build_user_context(
    name: str,
    place: str,
    tzinfo,
    birth_dt_local,
    weekday_name: str,
    ayan_choice: str,
    ayan: float,
    node_choice: str,
    house_choice: str,
    asc_rashi: str,
    moon_rashi: str,
    sun_rashi: str,
    paksha: str,
    t_num: int,
    t_name: str,
    nk_idx: int,
    nk_name: str,
    nk_pada: int,
    yoga_idx: int,
    yoga_name: str,
    kar_idx: int,
    kar_name: str,
    planets: dict,
    planet_houses: dict,
    planet_flags: dict,
    lordship_block: str,
    aspects_geo: list,
    dash_rows: list,
    jup_7_to_moon: bool,
    panchang_module,
) -> str:
    planet_lines = []
    for k in planets:
        pl_lon = planets[k]["lon"] % 360.0
        deg = pl_lon % 30.0
        house = planet_houses[k]
        rashi = panchang_module.rashi_name(pl_lon)
        flags = planet_flags.get(k, "")
        bits = [f"{k}: {rashi}, House {house}, {deg:.2f}°"]
        if flags:
            bits.append(f"[{flags}]")
        planet_lines.append(" ".join(bits))
    planets_block = "\\n".join(planet_lines)

    md_lines = [
        f"{r['Mahadasha Lord']}: {r['Start (local)']} → {r['End (local)']} ({r['Years']}y)"
        for r in dash_rows
    ]
    md_block = "\\n".join(md_lines)

    aspects_text = (
        "; ".join([f"{a['A']}-{a['B']} {a['type']}" for a in aspects_geo])
        or "None within orbs"
    )
    flags_summary = (
        "; ".join([f"{k}: {planet_flags[k]}" for k in planets if planet_flags.get(k)])
        or "None"
    )

    return f"""Name: {name or '-'}
Place/Timezone: {place} / {tzinfo.zone}
Birth (local): {birth_dt_local.strftime('%Y-%m-%d %H:%M')} ({weekday_name})
Ayanamsa: {ayan_choice} ({ayan:.4f}°)  •  Node: {node_choice}  •  Houses: {house_choice}

Ascendant (Lagna): {asc_rashi}
Moon Rashi: {moon_rashi}
Sun Rashi: {sun_rashi}

Panchanga:
- Paksha: {paksha}
- Tithi: {t_num} — {t_name}
- Nakshatra: {nk_idx} — {nk_name} (Pada {nk_pada})
- Yoga: {yoga_idx} — {yoga_name}
- Karana: {kar_idx} — {kar_name}

Planets with Houses (sidereal):
{planets_block}

Bhava lordship (from ascendant):
{lordship_block}

Computed flags per graha (retro/combust/exalt/debil):
{flags_summary}

Geometric aspects (within orbs): {aspects_text}

JUPITER_7TH_TO_MOON: {jup_7_to_moon}

Mahadasha (exact lines — reproduce verbatim in the 'Mahadasha (exact dates)' section):
```
{md_block}
```
"""


def run_analysis(
    client,
    model: str,
    style: str,
    user_context: str,
    max_tokens: int = 900,
    temperature: float = 0.7,
) -> Optional[str]:
    """Call OpenAI and return the analysis text, or raise on error."""
    sys_prompt = build_sys_prompt(style)
    logger.info("Requesting AI analysis: model=%s style=%s", model, style)
    chat = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": user_context},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return chat.choices[0].message.content or ""
