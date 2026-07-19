"""
jyotish/chart.py
----------------
Chart rendering functions (matplotlib).

Provides:
  draw_north_chart(asc_deg, planets_dict, show_degrees) -> matplotlib Figure
"""
from collections import defaultdict
from typing import Dict

import matplotlib.pyplot as plt


# Planet abbreviations used in the chart cells
_ABBR: Dict[str, str] = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa",
    "Rahu": "Ra", "Ketu": "Ke",
}

# (x, y) positions for each of the 12 house cells in the North-Indian diamond layout.
# Index 0 = House 1 (Lagna) at top-centre; index increases counter-clockwise.
_NI_POSITIONS = [
    (0.50, 0.90),  # 0: Lagna (top-centre)
    (0.75, 0.75),  # 1: Upper-right
    (0.90, 0.50),  # 2: Right-middle
    (0.75, 0.25),  # 3: Lower-right
    (0.50, 0.10),  # 4: Bottom-centre
    (0.25, 0.25),  # 5: Lower-left
    (0.10, 0.50),  # 6: Left-middle
    (0.25, 0.75),  # 7: Upper-left
    (0.50, 0.75),  # 8: Inner top
    (0.75, 0.50),  # 9: Inner right
    (0.50, 0.25),  # 10: Inner bottom
    (0.25, 0.50),  # 11: Inner left
]


def draw_north_chart(
    asc_deg: float,
    planets_dict: Dict[str, Dict[str, float]],
    show_degrees: bool = True,
) -> plt.Figure:
    """
    Render a North-Indian style Rashi chart.

    Parameters
    ----------
    asc_deg : float
        Sidereal longitude of the Ascendant (degrees).
    planets_dict : dict
        Mapping of planet name -> {"lon": float, "speed": float, ...}.
    show_degrees : bool
        If True, each planet label includes the degree within its sign.

    Returns
    -------
    matplotlib.figure.Figure
    """
    fig = plt.figure(figsize=(6, 6), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()

    # ── Frame (two diagonals + four sides) ──────────────────────────────────
    ax.plot([0, 1], [0, 1], lw=2, color="#F28C28")
    ax.plot([0, 1], [1, 0], lw=2, color="#2F80ED")
    ax.plot([0, 0], [0, 1], lw=3, color="#2ECC71")
    ax.plot([1, 1], [0, 1], lw=3, color="#E74C3C")
    ax.plot([0, 1], [0, 0], lw=3, color="#8D6E63")
    ax.plot([0, 1], [1, 1], lw=3, color="#8D6E63")

    asc_sign = int((asc_deg % 360.0) // 30)

    # ── Bucket planets into house cells ─────────────────────────────────────
    buckets: Dict[int, list] = defaultdict(list)
    for name_, vals in planets_dict.items():
        lonv = vals["lon"] % 360.0
        sign = int(lonv // 30)
        disp_index = (sign - asc_sign) % 12
        label = _ABBR.get(name_, name_)
        deg_in_sign = lonv % 30.0
        if show_degrees:
            label = f"{label} {deg_in_sign:.0f}°"
        buckets[disp_index].append((deg_in_sign, label))

    # ── Lagna marker ────────────────────────────────────────────────────────
    asc_x, asc_y = _NI_POSITIONS[0]
    ax.text(asc_x, asc_y, "Asc", fontsize=12, ha="center", va="center",
            fontweight="bold")

    # ── Place labels, stacking vertically to avoid overlap ──────────────────
    for idx in range(12):
        x, y = _NI_POSITIONS[idx]
        items = buckets.get(idx, [])
        if not items:
            continue
        items.sort()
        n = len(items)
        step = 0.065
        top = y + (step * (n - 1) / 2.0)
        fontsize = max(8, 11 - max(0, n - 1))
        for i, (_deg, label) in enumerate(items):
            yi = top - i * step
            ax.text(
                x, yi, label,
                fontsize=fontsize, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="0.7", alpha=0.7),
            )

    return fig
