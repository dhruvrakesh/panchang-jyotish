"""
jyotish/ai_prompt.py
---------------------
Prompt assembly and AI call for Vedic Jyotish analysis.

J2 fidelity revision (2026-07-19, see JYOTISH_FIDELITY_AUDIT_2026-07-19.md):
  * No hard-coded interpretive claims in the system prompt. The model may only
    state what the computed data says (flags, drishti, dasha) — the old
    unconditional "neecha-bhanga support" sentence is gone.
  * Western aspect vocabulary (square/trine/sextile) is forbidden; classical
    drishti terminology is required.
  * Engine-selectable via JYOTISH_AI_ENGINE ("gemini:<model>" or
    "openai:<model>"), automaton-style. Defaults to the OpenAI client passed
    by the app, so existing behaviour is unchanged unless the env var is set.

Provides:
  build_user_context(...)  -> str
  build_sys_prompt(style)  -> str
  run_analysis(client, model, style, context) -> str
"""
import logging
import os
from typing import Optional

logger = logging.getLogger("jyotish.ai_prompt")

_GROUNDING = (
    "GROUNDING RULES (mandatory): "
    "Use ONLY the data provided — never invent placements, dates, yogas or doshas. "
    "Use classical Parashari vocabulary: say 'drishti' (with the house-distance, e.g. "
    "'7th drishti'), never Western terms like 'square', 'trine', 'sextile' or 'conjunct "
    "aspect'. Mention debilitation/exaltation/retrogression/combustion ONLY if that flag "
    "appears in 'Computed flags'. Mention neecha-bhanga ONLY if a line 'Neecha-bhanga "
    "candidates:' lists it — otherwise do not raise the concept. "
    "State the bhava (house) for EVERY graha. "
    "In the Mahadasha section reproduce EXACTLY the lines between the triple backticks. "
    "Avoid deterministic health/finance/lifespan claims."
)


def build_sys_prompt(style: str) -> str:
    if style == "Clear & businesslike":
        return (
            "You are a careful, modern Jyotish analyst. Write a structured 300-500 word "
            "reading. " + _GROUNDING + " "
            "Sections: Overview; Panchanga & Temperament; Lagna & Chandra; "
            "Graha-by-Graha (with house); Drishti; Mahadasha (exact dates); Guidance."
        )
    # Classical (traditional)
    return (
        "You are a Vedic Jyotish scholar writing a balanced, evidence-based 300-500 word "
        "reading. " + _GROUNDING + " "
        "In the Graha-by-Graha section use the form 'Sun — sign, House N, deg, [flags]'. "
        "Sections: Overview; Panchanga & Temperament; Lagna & Chandra; Graha-by-Graha; "
        "Drishti; Mahadasha (exact dates); Guidance."
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
    planets_block = "\n".join(planet_lines)

    md_lines = [
        f"{r['Mahadasha Lord']}: {r['Start (local)']} → {r['End (local)']} ({r['Years']}y)"
        for r in dash_rows
    ]
    md_block = "\n".join(md_lines)

    aspects_text = (
        "; ".join([f"{a['A']}-{a['B']} {a['type']}" for a in aspects_geo])
        or "None within orbs"
    )
    flags_summary = (
        "; ".join([f"{k}: {planet_flags[k]}" for k in planets if planet_flags.get(k)])
        or "None"
    )

    # Computed facts only — the model may describe these, nothing more.
    moon_flags = (planet_flags.get("Moon") or "").lower()
    moon_debilitated = "debil" in moon_flags
    computed_facts = [
        f"- Jupiter casts 7th drishti to the Moon: {bool(jup_7_to_moon)}",
        f"- Moon debilitated: {moon_debilitated}",
    ]
    # Neecha-bhanga is NOT asserted here: candidates are only listed if upstream
    # code computes a classical bhanga condition. Until then the model must stay
    # silent on it (see GROUNDING RULES).
    computed_block = "\n".join(computed_facts)

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

Computed facts (describe only what is True; do not extrapolate):
{computed_block}

Geometric aspects (within orbs): {aspects_text}

Mahadasha (exact lines — reproduce verbatim in the 'Mahadasha (exact dates)' section):
```
{md_block}
```
"""


def _run_gemini(model_name: str, sys_prompt: str, user_context: str,
                max_tokens: int, temperature: float) -> Optional[str]:
    """Gemini path (JYOTISH_AI_ENGINE=gemini:<model>). Raises on failure so the
    caller can fall back to OpenAI."""
    import google.generativeai as genai  # optional dep: pip install google-generativeai
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)
    gm = genai.GenerativeModel(model_name, system_instruction=sys_prompt)
    resp = gm.generate_content(
        user_context,
        generation_config={"max_output_tokens": max_tokens, "temperature": temperature},
    )
    return resp.text or ""


def run_analysis(
    client,
    model: str,
    style: str,
    user_context: str,
    max_tokens: int = 900,
    temperature: float = 0.7,
) -> Optional[str]:
    """Run the AI analysis.

    Engine selection (automaton-style): if JYOTISH_AI_ENGINE is set to
    'gemini:<model>' the Gemini API is used (falling back to OpenAI on any
    error); 'openai:<model>' overrides the model name; unset -> the OpenAI
    client/model passed in, exactly as before.
    """
    sys_prompt = build_sys_prompt(style)
    engine = (os.environ.get("JYOTISH_AI_ENGINE") or "").strip()

    if engine.startswith("gemini:"):
        gem_model = engine.split(":", 1)[1] or "gemini-2.5-flash"
        try:
            logger.info("Requesting AI analysis via Gemini: model=%s style=%s", gem_model, style)
            return _run_gemini(gem_model, sys_prompt, user_context, max_tokens, temperature)
        except Exception as e:
            logger.warning("Gemini engine failed (%s); falling back to OpenAI.", e)

    if engine.startswith("openai:"):
        model = engine.split(":", 1)[1] or model

    if client is None:
        raise RuntimeError(
            "No AI engine available: OpenAI client not configured and "
            "JYOTISH_AI_ENGINE gemini path failed or unset."
        )
    logger.info("Requesting AI analysis via OpenAI: model=%s style=%s", model, style)
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
