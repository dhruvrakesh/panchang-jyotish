# Jyotish Panchang & Horoscope — Fidelity Audit & Phased Plan

**Date:** 2026-07-19 · **Method:** every number in the sample report
(`horoscope_report.pdf`, birth 1988-08-21 04:15 IST, 32.2997°N 75.884°E, Lahiri,
mean node, whole sign) was **independently recomputed** from the published sidereal
longitudes, and every suspected defect was **confirmed in source** (`jyotish/dasha.py`,
`ai_prompt.py`, `panchang.py`, `pdf_export.py`) before being asserted. Nothing below
is inferred without evidence.

---

## 1. What is classically CORRECT (verified by recomputation)

| Element | Report | Independent check | Verdict |
|---|---|---|---|
| Ephemeris & ayanamsa | Swiss Ephemeris, Lahiri 23.6984° | Lahiri for 1988-08-21 ≈ 23°42′ | ✅ |
| Tithi | Śukla Aṣṭamī (8) | (217.827−124.408) = 93.42° → ⌊93.42/12⌋+1 = 8, Śukla | ✅ |
| Nakṣatra | Anurādhā pada 2 | 217.827/13.3̅ = 16.34 → #17; (4.494/3.3̅)→pada 2 | ✅ |
| Yoga | Indra (26) | (124.408+217.827)=342.23/13.3̅ = 25.67 → #26 | ✅ |
| Karaṇa | Bava (16) | ⌊93.42/6⌋+1 = 16; (16−2) mod 7 = 0 → Bava | ✅ |
| Karaṇa tables | Kimstughna 1st; Śakuni/Catuṣpada/Nāga fixed at end | matches BPHS Pañcāṅga count; alternate tradition documented in code | ✅ |
| Whole-sign bhāvas | Cancer lagna; Su H2, Mo H5, Ma H9, Ju H11, Ve H12, Sa H6, Ra H8 | consistent throughout | ✅ |
| Parāśari dṛṣṭi table | 13 rows | every row verified: universal 7th + Mars 4/8 + Jupiter 5/9 + Saturn 3/10, nothing spurious | ✅ |
| Mahādaśā balance | Saturn 12.6y | Anurādhā = Saturn-ruled; (1−0.337)×19 = 12.596y | ✅ |
| Dignities | Sun own/Mūlatrikoṇa (4.41° Leo < 20°), Moon debilitated (Scorpio) | correct | ✅ |
| Node choice | Mean node, user-selectable | classical siddhāntic practice; defensible default | ✅ |

**The astronomical and pañcāṅga core is faithful.** Swiss Ephemeris + Lahiri +
whole-sign + correctly implemented Parāśari dṛṣṭi is the credible, standard stack.

## 2. Defects found (each confirmed in code)

**D1 · Antardaśā balance algorithm — classically WRONG (the one real math bug).**
`antardasha_for_segment()` rescaled all nine antardaśās *proportionally* into the
first (balance) mahādaśā. BPHS rule: a birth partway through a mahādaśā enters the
antardaśā cycle **mid-way** — prior antardaśās are already elapsed; the rest run at
full length. For this chart, birth at 6.40y into Saturn falls in **Saturn/Ketu**
(Sat 3.008 + Merc 2.692 = 5.70 < 6.40 < 6.81), yet the report shows a fresh
Saturn/Saturn of 728 days (= full 1,099d × 0.663 — exactly the tell-tale rescale).
**Fixed** in the delivered `dasha.py` (anchor-at-end + clip method; call-site
compatible; full mahādaśās unchanged) with 3-test regression suite — all passing.

**D2 · Hard-coded "neecha-bhaṅga" claim in the system prompt.** `ai_prompt.py`
instructs the model to print *"Jupiter casts full 7th drishti to the Moon
(neecha-bhanga support)"* whenever Jupiter opposes the Moon — for **every chart**,
including charts where the Moon is not debilitated (no nīca → no bhaṅga possible),
and even for this chart the claim is loose: Jupiter's dṛṣṭi is not among the standard
nīca-bhaṅga conditions (those involve the debilitation-sign lord / exaltation lord
in kendra etc.). A chart-specific interpretation is baked into a universal prompt.

**D3 · Western vocabulary leaking into a Jyotiṣa reading.** The AI text says
"Sun-Moon **square**" — a Western aspect concept with no Parāśari meaning (the Sun
has no 4th/10th dṛṣṭi). The prompt does not forbid Western terminology.

**D4 · Report formatting.** Raw markdown (`###`, `**`) rendered literally in the
PDF (no md→PDF conversion in `pdf_export.py`); **lagna degree absent** anywhere in
the report; North-Indian chart has **no rāśi numbers** in the houses; heading leaks
the internal spec "(300–500 words)"; antardaśā days shown as "728.0"; **zero
citations** (no ephemeris version, ayanāṃśa reference, or śāstra basis) and no
disclaimer.

**D5 · Year-length constant.** 365.2425 (Gregorian) used for daśā years; standard
Jyotiṣa software convention is 365.25. Drifts days over multi-decade daśās vs
almanacs. Changed to `YEAR_DAYS = 365.25`, documented as an explicit choice.

## 3. Phased plan (surgical; app keeps running throughout)

**J1 · Correctness (delivered today).** New `jyotish/dasha.py` (D1 + D5 fixed, same
API) + `tests/test_dasha_balance.py` (3 regression tests, passing). *Gate:*
`python -m pytest tests/` on Windows — existing `test_dasha.py` must stay green; if
it asserted the old proportional behaviour, update it citing this audit.

**J2 · Truthful AI layer (one commit).** In `ai_prompt.py`: delete the hard-coded
nīca-bhaṅga instruction; instead pass **computed flags** (moon_debilitated,
jupiter_7th_drishti_to_moon, …) and let the text state only what is computed;
forbid Western aspect vocabulary ("square/trine/sextile") and require dṛṣṭi
terminology; require the model to reference the provided data only (already partly
enforced). *Gate:* regenerate this same chart; diff the summary.

**J3 · Report quality (pdf_export, one commit).** Convert AI markdown to proper
paragraphs/bold; add lagna degree row to the header table and rāśi numbers to the
chart houses; karaṇa shown as "Bava (2nd half of Aṣṭamī)"; integer days; add a
**Methodology & Sources** block: Swiss Ephemeris version, Lahiri (Chitrapaksha)
citation, node/houses/year-length choices, BPHS references for dṛṣṭi & Vimśottarī,
and a "computed positions are deterministic; interpretation is AI-assisted"
disclaimer. *Gate:* regenerate PDF, visual before/after.

**J4 · AI engine choice.** Recommendation: **Gemini 2.5 Flash primary, OpenAI
fallback**, via the automaton's proven engine-string pattern
(`JYOTISH_AI_ENGINE=gemini:gemini-2.5-flash`, fallback `openai:gpt-4o-mini`).
Rationale: ~10–20× cheaper per reading than GPT-4o; the automaton has already
demonstrated Gemini's quality on śāstric Sanskrit content at scale; one shared key-
management pattern across your projects; and OpenAI stays wired (key just renewed)
so a one-line env change swaps engines. The interpretive layer is deterministic-
data-in → prose-out, where Flash is amply sufficient; offer Pro per-reading for a
"scholarly" mode if desired. *Gate:* same chart through both engines, side-by-side.

## 4. What was deliberately NOT changed

`vimshottari_from_birth` logic (verified correct), the pañcāṅga module (verified
correct), the aspect engine (verified correct), the Streamlit UI, and the existing
OpenAI path (fallback, not removal). The fix surface is exactly one function, one
constant, and — pending your go — one prompt file and one exporter.
