"""
jyotish/pdf_export.py
---------------------
ReportLab PDF export for Jyotish horoscope reports.

J3 report-quality revision (2026-07-19, see JYOTISH_FIDELITY_AUDIT_2026-07-19.md):
  * AI markdown (###, **bold**, bullets) rendered properly instead of literally
  * Ascendant (Lagna) rasi + degree added to the header table
  * Karana labelled with its half-tithi ("Bava — 2nd half of Ashtami")
  * Antardasha days as whole numbers
  * "Interpretive Summary" heading no longer leaks the internal word-count spec
  * New "Methodology & Sources" section: ephemeris, ayanamsa, classical
    references, year-length convention, AI-assistance disclaimer

Provides:
  build_pdf_bytes(**kwargs) -> bytes
"""
import io
import logging
import os
import re

import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from . import dasha as dasha_mod
from .chart import draw_north_chart
from .panchang import RASHIS

logger = logging.getLogger("jyotish.pdf_export")


# ── Font registration ──────────────────────────────────────────────────────────
def _register_font_safe() -> str:
    try:
        font_path = os.path.join(os.path.dirname(__file__), "..", "DejaVuSans.ttf")
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
            return "DejaVuSans"
    except Exception:
        pass
    return "Helvetica"


_BASE_FONT = _register_font_safe()


def _styles():
    styles = getSampleStyleSheet()
    for s in ["Title", "Normal", "Heading1", "Heading2", "Heading3"]:
        styles[s].fontName = _BASE_FONT
    styles.add(ParagraphStyle(name="Small", fontName=_BASE_FONT, fontSize=9, leading=11))
    styles.add(ParagraphStyle(name="Meta",  fontName=_BASE_FONT, fontSize=10, leading=12))
    styles.add(ParagraphStyle(name="MdBullet", fontName=_BASE_FONT, fontSize=10,
                              leading=13, leftIndent=14, bulletIndent=4))
    return styles


def _ascii_safe(s) -> str:
    """Transliterate common Sanskrit diacritics to ASCII for Helvetica compatibility."""
    if not isinstance(s, str):
        s = str(s)
    repl = {
        "ā": "a", "Ā": "A", "ī": "i", "Ī": "I", "ū": "u", "Ū": "U",
        "ṛ": "r", "Ṛ": "R", "ṅ": "n", "ñ": "n", "ś": "s", "Ś": "S",
        "ṣ": "s", "Ṣ": "S", "ṭ": "t", "Ṭ": "T", "ḍ": "d", "Ḍ": "D",
        "ṃ": "m", "Ṃ": "M", "–": "-", "—": "-", "‘": "'",
        "“": '"', "”": '"',
    }
    return "".join(repl.get(ch, ch) for ch in s)


def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _md_inline(s: str) -> str:
    """Escape XML, then convert **bold** and *italic* to ReportLab markup."""
    s = _xml_escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", s)
    return s


def _md_to_flowables(text: str, styles) -> list:
    """Render the AI's markdown-ish output as proper PDF flowables.
    Handles: ### headings, **bold**, *italic*, '- ' bullets, ``` fences
    (rendered as plain small text), and blank-line paragraph breaks."""
    flow = []
    para_buf = []

    def flush():
        if para_buf:
            joined = " ".join(para_buf).strip()
            if joined:
                flow.append(Paragraph(_md_inline(_ascii_safe(joined)), styles["Normal"]))
                flow.append(Spacer(1, 0.16 * cm))
            para_buf.clear()

    in_fence = False
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            if stripped:
                flow.append(Paragraph(_xml_escape(_ascii_safe(stripped)), styles["Small"]))
            continue
        if not stripped:
            flush()
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush()
            flow.append(Paragraph(_md_inline(_ascii_safe(m.group(2))), styles["Heading3"]))
            flow.append(Spacer(1, 0.08 * cm))
            continue
        if stripped.startswith(("- ", "• ")):
            flush()
            flow.append(Paragraph("• " + _md_inline(_ascii_safe(stripped[2:])),
                                  styles["MdBullet"]))
            continue
        para_buf.append(stripped)
    flush()
    return flow


def _table(rows, col_widths, header_row=True):
    """Build a styled ReportLab Table."""
    t = Table(rows, colWidths=col_widths)
    ts = [
        ("FONT", (0, 0), (-1, -1), _BASE_FONT, 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if header_row:
        ts.append(("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey))
    t.setStyle(TableStyle(ts))
    return t


# ── Main export function ───────────────────────────────────────────────────────
def build_pdf_bytes(
    *,
    name: str,
    place: str,
    tzname: str,
    birth_dt_local,
    weekday_name: str,
    lat: float,
    lon: float,
    ayan_choice: str,
    ayan: float,
    node_choice: str,
    house_choice: str,
    asc: float,
    planets: dict,
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
    df_plan,
    aspects_geo: list,
    aspects_drishti: list,
    timeline: list,
    dash_rows: list,
    analysis_text: str = "",
    show_western_aspects: bool = False,
) -> bytes:
    """Build and return PDF bytes for the full horoscope report."""

    # ── Chart PNG ──────────────────────────────────────────────────────────────
    chart_buf = io.BytesIO()
    fig = draw_north_chart(asc, planets, show_degrees=True)
    fig.savefig(chart_buf, format="png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    chart_buf.seek(0)

    # ── Document ───────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        topMargin=1.4 * cm, bottomMargin=1.4 * cm,
        title="Jyotish Panchang & Horoscope",
    )
    styles = _styles()
    story = []

    # Title
    story.append(Paragraph(_ascii_safe("Jyotish Panchang & Horoscope"), styles["Title"]))
    story.append(Spacer(1, 0.2 * cm))

    # Ascendant (Lagna): rasi + degree within rasi (J3: previously absent)
    asc_norm = asc % 360.0
    asc_rasi = RASHIS[int(asc_norm // 30.0)]
    asc_deg_in_rasi = asc_norm % 30.0

    # Meta table
    meta_data = [
        ["Name",        _ascii_safe(name or "-")],
        ["Place",       _ascii_safe(place)],
        ["Timezone",    _ascii_safe(tzname)],
        ["Birth (local)", birth_dt_local.strftime("%Y-%m-%d %H:%M") + f"  ({weekday_name})"],
        ["Coordinates", f"{lat:.4f}°, {lon:.4f}°"],
        ["Ascendant (Lagna)", _ascii_safe(f"{asc_rasi} — {asc_deg_in_rasi:.2f}° "
                                          f"(sidereal {asc_norm:.4f}°)")],
        ["Settings",    _ascii_safe(
            f"Ayanamsa={ayan_choice} ({ayan:.4f}); Node={node_choice}; Houses={house_choice}"
        )],
    ]
    meta_tbl = Table(meta_data, colWidths=[3.2 * cm, 12 * cm], hAlign="LEFT")
    meta_tbl.setStyle(TableStyle([
        ("FONT",           (0, 0), (-1, -1), _BASE_FONT, 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
        ("LINEBELOW",      (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 0.25 * cm))

    # Chart
    story.append(Paragraph("Rasi Chart (North-Indian)", styles["Heading2"]))
    story.append(Spacer(1, 0.1 * cm))
    story.append(Image(chart_buf, width=14 * cm, height=14 * cm, kind="proportional"))
    story.append(Spacer(1, 0.2 * cm))

    # Panchang (J3: karana labelled with its half-tithi — odd slot = 1st half)
    kar_half = "1st" if (kar_idx % 2 == 1) else "2nd"
    p_rows = [
        ["Paksha",    _ascii_safe(paksha),
         "Tithi",     f"{t_num} - {_ascii_safe(t_name)}"],
        ["Nakshatra", f"{nk_idx} - {_ascii_safe(nk_name)} (Pada {nk_pada})",
         "Yoga",      f"{yoga_idx} - {_ascii_safe(yoga_name)}"],
        ["Karana",    f"{kar_idx} - {_ascii_safe(kar_name)} ({kar_half} half of {_ascii_safe(t_name)})",
         "", ""],
    ]
    story.append(Paragraph("Panchang", styles["Heading2"]))
    p_tbl = Table(p_rows, colWidths=[2.6 * cm, 7.0 * cm, 2.6 * cm, 3.0 * cm], hAlign="LEFT")
    p_tbl.setStyle(TableStyle([
        ("FONT",   (0, 0), (-1, -1), _BASE_FONT, 10),
        ("GRID",   (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(p_tbl)
    story.append(Spacer(1, 0.2 * cm))

    # Planet positions
    story.append(Paragraph("Sidereal Planetary Positions", styles["Heading2"]))
    plan_rows = [["Body", "Longitude", "Rasi", "Deg in Rasi", "Speed"]]
    for row in df_plan.reset_index().to_dict(orient="records"):
        plan_rows.append([
            _ascii_safe(row["Body"]),
            f"{row['Longitude (°)']:.4f}",
            _ascii_safe(str(row.get("Rāśi", ""))),
            f"{row.get('Deg in Rāśi', 0):.2f}",
            f"{row.get('Speed (°/day)', 0):.4f}",
        ])
    story.append(_table(plan_rows, [2.5 * cm, 3.5 * cm, 5.5 * cm, 3.0 * cm, 3.0 * cm]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(PageBreak())

    # Western aspects (optional)
    if show_western_aspects and aspects_geo:
        story.append(Paragraph("Aspects (Geometric)", styles["Heading2"]))
        geo_rows = [["A", "B", "Type", "Delta"]]
        for a in aspects_geo:
            geo_rows.append([
                _ascii_safe(a["A"]), _ascii_safe(a["B"]),
                _ascii_safe(a["type"]), str(a.get("delta", "")),
            ])
        story.append(_table(geo_rows, [4.0 * cm, 4.0 * cm, 4.0 * cm, 3.5 * cm]))
        story.append(Spacer(1, 0.2 * cm))

    # Parashari drishti
    story.append(Paragraph("Parashari graha-drsti (classical)", styles["Heading2"]))
    dr_rows = [["Aspecting", "Aspected Sign", "Type"]]
    for a in aspects_drishti:
        dr_rows.append([_ascii_safe(a["A"]), _ascii_safe(a["B"]), _ascii_safe(a["type"])])
    story.append(_table(dr_rows, [5.0 * cm, 5.0 * cm, 5.0 * cm]))
    story.append(PageBreak())

    # Vimshottari Mahadasha
    story.append(Paragraph("Vimshottari Mahadasha", styles["Heading2"]))
    d_rows = [["Lord", "Start", "End", "Years"]]
    for r in dash_rows:
        d_rows.append([
            _ascii_safe(r["Mahadasha Lord"]),
            r["Start (local)"], r["End (local)"], str(r["Years"]),
        ])
    story.append(_table(d_rows, [4.0 * cm, 4.0 * cm, 4.0 * cm, 3.0 * cm]))
    story.append(Spacer(1, 0.2 * cm))

    # Antardasha (first Mahadasha) — J3: whole days; mid-cycle entry per J1 fix
    story.append(Paragraph("Antardasha (first Mahadasha)", styles["Heading3"]))
    try:
        first_md = timeline[0]
        antar = dasha_mod.antardasha_for_segment(
            first_md["lord"], first_md["start"], first_md["end"]
        )
        a_rows = [["Antar Lord", "Start", "End", "Days"]]
        for a in (antar or []):
            a_rows.append([
                _ascii_safe(a["lord"]),
                a["start"].strftime("%Y-%m-%d"),
                a["end"].strftime("%Y-%m-%d"),
                f"{a.get('days', (a['end'] - a['start']).total_seconds() / 86400.0):.0f}",
            ])
        if len(a_rows) == 1:
            a_rows.append(["-", "-", "-", "-"])
        story.append(Paragraph(
            "The first mahadasha is a balance period: its antardasha cycle is entered "
            "mid-way per the classical Vimshottari rule; the first row shows only the "
            "portion remaining after birth.", styles["Small"]))
        story.append(Spacer(1, 0.08 * cm))
    except Exception:
        logger.exception("Antardasha build failed")
        a_rows = [["Antar Lord", "Start", "End", "Days"], ["-", "-", "-", "-"]]
    story.append(_table(a_rows, [4.0 * cm, 4.0 * cm, 4.0 * cm, 3.0 * cm]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(PageBreak())

    # AI Analysis (J3: proper markdown rendering; internal spec removed from title)
    story.append(Paragraph("Interpretive Summary (AI-assisted)", styles["Heading2"]))
    if analysis_text:
        story.extend(_md_to_flowables(analysis_text, styles))
    else:
        story.append(Paragraph(
            "No AI analysis generated in this session. "
            "Use the 'Generate Analysis' button in the app, then export again.",
            styles["Small"],
        ))

    # Methodology & Sources (J3: previously absent)
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Methodology & Sources", styles["Heading2"]))
    method_lines = [
        "Positions: Swiss Ephemeris (pyswisseph), sidereal zodiac.",
        f"Ayanamsa: {_ascii_safe(ayan_choice)} ({ayan:.4f}° at birth). Lahiri = Chitrapaksha "
        "ayanamsa as standardised by the Indian Calendar Reform Committee (1956).",
        f"Nodes: {_ascii_safe(node_choice)}. Houses: {_ascii_safe(house_choice)}.",
        "Panchanga: tithi = 12° steps of Moon−Sun elongation; nakshatra = 13°20′ arcs; "
        "yoga = 13°20′ steps of Sun+Moon; karana = half-tithi (BPHS, Panchanga chapters). "
        "Values are computed for the moment of birth.",
        "Graha-drishti: full 7th for all grahas plus special drishti of Mars (4th, 8th), "
        "Jupiter (5th, 9th) and Saturn (3rd, 10th), per Brihat Parashara Hora Shastra.",
        f"Vimshottari dasha: 120-year cycle from the Moon's nakshatra lord; balance by "
        f"fraction elapsed; antardashas at full classical length with mid-cycle entry for "
        f"the balance period; year = {dasha_mod.YEAR_DAYS} days.",
        "The tables above are deterministic computations. The Interpretive Summary is "
        "AI-assisted prose generated strictly from those computed values; it is offered "
        "for reflection, not as deterministic prediction.",
    ]
    for ln in method_lines:
        story.append(Paragraph("• " + _xml_escape(ln), styles["Small"]))
        story.append(Spacer(1, 0.06 * cm))

    # Page-number footer
    def _footer(canvas, doc):
        canvas.setFont(_BASE_FONT, 9)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(A4[0] - 1.5 * cm, 1.0 * cm, f"Page {doc.page}")
        canvas.setFillColor(colors.black)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf.getvalue()
