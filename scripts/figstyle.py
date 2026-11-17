"""Shared figure style: BIH theme palette and type, one place for every figure script.

The hues are the BIH PowerPoint theme accents (teal, coral, ochre, lavender, dark
red, navy). The four *source* colours are those hues re-stepped in lightness and
chroma so they pass the data-viz palette checks (colour-vision-deficiency
separation, chroma floor, contrast) on a white surface, all pairs:

    node <dataviz skill>/scripts/validate_palette.js \\
        "#1e97a5,#ea6a64,#9e7113,#7871d2" --mode light --pairs all
    worst CVD pair ΔE 8.7, normal vision 15.8, all >= 3:1 (2026-11-17)

Sources keep one colour each across every figure and slide:

    oBDS      teal       NABON     coral      B1MG      ochre
    Senologie lavender   INT Milan dark red   hub       navy (sequential ramp)
"""
from __future__ import annotations

import matplotlib

# --- BIH theme, as in the slide template -------------------------------------
NAVY = "#003754"      # dk1: slide background, hub
RED = "#AF1821"       # accent1
CORAL = "#EA5451"     # accent2
PINK = "#FFB0AC"      # accent3
OCHRE = "#9D7220"     # accent4
TEAL = "#009AA9"      # accent5
LAVENDER = "#7876B6"  # accent6

# --- data colours: BIH hues, stepped to pass the palette checks ----------------
S_TEAL = "#1e97a5"
S_CORAL = "#ea6a64"
S_OCHRE = "#9e7113"
S_LAVENDER = "#7871d2"
S_RED = RED

# --- neutrals -----------------------------------------------------------------
INK = "#1A1A1A"
INK2 = "#52514E"
MUTED = "#898781"
GRID = "#DDDCD6"
BAND = "#F3F3F0"
BAND2 = "#E9E8E3"
SURF = "#FFFFFF"
OOS = "#B3B2AC"       # out-of-scope / not clinical cancer content
OOS_DARK = "#7C7B77"

SRC_COLOUR = {"mii-onko-obds": S_TEAL, "nabon-mammacarcinoom": S_CORAL, "b1mg-cmd": S_OCHRE,
              "senologie-datenkranz": S_LAVENDER, "int-breast": S_RED}
CARRIAGE_COLOUR = {"coded-finding": S_TEAL, "extend-model": S_LAVENDER, "new-module": S_OCHRE,
                   "out-of-scope": OOS, "review": BAND2}
HUB = NAVY
HUB_RAMP = ["#EEF1F3", "#B7C8D2", "#6C8FA3", "#2F607B", NAVY]   # coverage 0 .. 1, one hue
GENERIC = S_CORAL      # pan-cancer content with no hub home
BREAST = RED           # of which breast-specific (nested, darker step of the same hue)


def apply(scale: float = 1.0) -> None:
    """Set matplotlib defaults: Fira Sans (falls back to DejaVu), BIH ink colours."""
    matplotlib.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Fira Sans", "DejaVu Sans"],
        "font.size": 9 * scale,
        "text.color": INK,
        "axes.labelcolor": INK2,
        "axes.edgecolor": GRID,
        "xtick.color": INK2,
        "ytick.color": INK,
        "legend.fontsize": 8.5 * scale,
        "figure.facecolor": SURF,
        "savefig.facecolor": SURF,
        "hatch.linewidth": 0.6,
    })
