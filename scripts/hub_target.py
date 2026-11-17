#!/usr/bin/env python3
"""Target diagram: how far from the ECCDM hub does each kind of content sit?

Polar layout.
  * angle  = clinical domain, clockwise along the care pathway
             (patient → diagnosis → imaging → pathology → therapy → follow-up,
             plus a registry / organisation sector)
  * radius = carriage, i.e. distance from the hub:
             core      ECCDM's own models (filled by hub coverage)
             ring 1    extend-model  — finer attributes on a model ECCDM has
             ring 2    by-reference  — coded findings attached by evidence reference
             ring 3    new-module    — needs a new hub model
             outside   out-of-scope  — not clinical cancer content
  * bubble area = unmapped source fields in that category; the inner disc is
    the breast-cancer-specific share (keyword-tagged, a lower bound)
  * the 4-cell strip under a bubble marks which sources contribute
    (oBDS · NABON · B1MG · Senologie).

Reuses the clustering (classify) and tagging (specificity) from inverse_gaps.py
and the hub coverage from hub/eccdm/elements.csv + mappings/*.sssom.tsv.
Writes docs/hub-target.png.

Usage:
    python scripts/hub_target.py [--out docs/hub-target.png]
"""
from __future__ import annotations

import argparse
import csv
import glob
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Wedge

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import inverse_gaps as ig  # noqa: E402

REPO = ig.REPO
HUB = REPO / "hub" / "eccdm" / "elements.csv"
DEFAULT_OUT = REPO / "docs" / "hub-target.png"

# ---------------------------------------------------------------- layout ---
SECTORS = [  # clockwise from the top
    ("Patient &\nhistory", ["CancerPatient"]),
    ("Diagnosis &\nstaging", ["CancerConditionAtDiagnosis", "CancerStage"]),
    ("Imaging", ["Imaging"]),
    ("Pathology &\nbiomarkers", []),
    ("Therapy", ["SystemicTreatment", "Radiotherapy", "Surgery", "ActiveSurveillance"]),
    ("Follow-up &\noutcome", ["LastFollowUp", "ClinicalCancerProgression",
                              "OverallCancerTreatmentResponse"]),
    ("Registry &\norganisation", []),
]
# category -> (sector index, short label)
CATEGORY = {
    "Patient history / risk factors": (0, "patient history /\nrisk factors"),
    "Psychosocial / supportive care": (0, "psychosocial\ncare"),
    "Administrative / identifiers / contact": (0, "administrative /\nidentifiers"),
    "Diagnosis / staging detail (TNM, localisation, side)": (1, "staging detail\n(TNM, side, localisation)"),
    "Clinical examination / performance status": (1, "clinical exam /\nperformance"),
    "Imaging findings / BI-RADS": (2, "imaging findings /\nBI-RADS"),
    "Pathology detail": (3, "pathology\ndetail"),
    "Biomarker / receptor status": (3, "biomarkers /\nreceptors"),
    "Molecular tests / genomics": (3, "molecular\ntests"),
    "Genomics / biobank infrastructure": (3, "genomics / biobank\ninfrastructure"),
    "Treatment detail (drug, dose, cycles, fractions, technique)": (4, "treatment detail\n(drug, dose, fractions)"),
    "Surgery / procedure detail (biopsy, implants, planning)": (4, "surgery /\nprocedure detail"),
    "Adverse events / complications": (4, "adverse\nevents"),
    "Tumour board / MDO": (4, "tumour\nboard"),
    "Study participation": (4, "study\nparticipation"),
    "Follow-up, response, death & second tumour": (5, "follow-up / death /\n2nd tumour"),
    "Registry transport / XML structure": (6, "registry transport /\nXML structure"),
    "Referral / care setting": (6, "referral /\ncare setting"),
    "Other-entity & paediatric registry modules (prostate, colorectal, melanoma, DKKR)":
        (6, "other-entity\nmodules"),
}
RING = {"extend-model": 1, "by-reference": 2, "new-module": 3, "out-of-scope": 4}
RING_LABEL = {1: "ring 1\nextend an\nexisting model", 2: "ring 2\nattach by\nevidence reference",
              3: "ring 3\nnew hub\nmodule", 4: "outside\nnot clinical\ncancer content"}
R_CORE = 1.2
R_EDGE = [R_CORE, 2.35, 3.5, 4.65, 5.8]      # ring boundaries
R_MAX_BUBBLE = 0.36                           # radius of the largest bubble
LABEL_SEP = 2                                 # separator line (index) that carries the ring labels
CORE_SHORT = {"CancerPatient": "CancerPatient",
              "CancerConditionAtDiagnosis": "Condition\nAtDiagnosis", "CancerStage": "CancerStage",
              "Imaging": "Imaging", "SystemicTreatment": "SystemicTreatment",
              "Radiotherapy": "Radiotherapy", "Surgery": "Surgery",
              "ActiveSurveillance": "ActiveSurveillance", "LastFollowUp": "LastFollowUp",
              "ClinicalCancerProgression": "Progression",
              "OverallCancerTreatmentResponse": "TreatmentResponse"}

# ---------------------------------------------------------------- colours --
import figstyle as fs  # noqa: E402

C_HUB = fs.HUB
C_HUB_RAMP = fs.HUB_RAMP
C_GENERIC = fs.GENERIC
C_BREAST = fs.BREAST
C_OOS = fs.OOS
C_OOS_IN = fs.OOS_DARK
C_INK = fs.INK
C_INK2 = fs.INK2
C_MUTED = fs.MUTED
C_GRID = fs.GRID
C_SURF = fs.SURF
C_BAND = ["#ffffff", fs.BAND, "#ffffff", fs.BAND, fs.BAND2]
FS = 1.0                                     # font scale, raised in --slide mode
SRC_ORDER = list(ig.SOURCES)
SRC_SHORT = {"mii-onko-obds": "oBDS", "nabon-mammacarcinoom": "NABON",
             "b1mg-cmd": "B1MG", "senologie-datenkranz": "Senologie"}


def collect():
    mapped_subj, mapped_obj = set(), set()
    for f in glob.glob(str(ig.MAPPINGS / "*__to__eccdm.sssom.tsv")):
        for r in csv.DictReader([l for l in open(f) if not l.startswith("#")],
                                delimiter="\t"):
            if r.get("subject_id"):
                mapped_subj.add(r["subject_id"])
            if r.get("object_id"):
                mapped_obj.add(r["object_id"])
    # hub coverage per model
    size, covered = Counter(), Counter()
    for r in csv.DictReader(HUB.open(encoding="utf-8")):
        size[r["model"]] += 1
        if r["id"] in mapped_obj:
            covered[r["model"]] += 1
    # outside content per category
    n_all = Counter(); n_breast = Counter(); srcs = defaultdict(Counter); carriage = {}
    for src, path in ig.SOURCES.items():
        for r in ig.load_source(REPO / path):
            if r["id"] in mapped_subj:
                continue
            m, c = ig.classify(r)
            carriage[m] = c
            n_all[m] += 1
            srcs[m][src] += 1
            if ig.specificity(r) == "breast":
                n_breast[m] += 1
    return size, covered, n_all, n_breast, srcs, carriage


def polar(r, theta_deg):
    th = math.radians(90 - theta_deg)           # 0° = top, clockwise
    return r * math.cos(th), r * math.sin(th)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--slide", action="store_true",
                    help="slide version: no title, no legend, larger type (docs/hub-target-slide.png)")
    args = ap.parse_args()
    global FS
    FS = 1.55 if args.slide else 1.0
    fs.apply()
    if args.slide and args.out == DEFAULT_OUT:
        args.out = DEFAULT_OUT.with_name("hub-target-slide.png")
    size, covered, n_all, n_breast, srcs, carriage = collect()

    nsec = len(SECTORS)
    sw = 360 / nsec
    fig, ax = plt.subplots(figsize=(15.5, 16), facecolor=C_SURF)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-6.6, 6.6); ax.set_ylim(-7.0, 6.4)

    # ring bands (matplotlib wedges go counter-clockwise from +x; we only need
    # full annuli here, so orientation does not matter)
    for k in range(1, 5):
        ax.add_patch(Wedge((0, 0), R_EDGE[k], 0, 360, width=R_EDGE[k] - R_EDGE[k - 1],
                           facecolor=C_BAND[k], edgecolor=C_GRID, linewidth=0.8, zorder=0))
    # sector separators
    for i in range(nsec):
        x, y = polar(R_EDGE[-1], i * sw)
        ax.plot([0, x], [0, y], color=C_GRID, linewidth=0.8, zorder=1)

    # core: one wedge per sector, filled by hub coverage of that sector's models
    for i, (name, models) in enumerate(SECTORS):
        a0, a1 = 90 - (i + 1) * sw, 90 - i * sw        # mpl angles (ccw from +x)
        tot = sum(size[m] for m in models); cov = sum(covered[m] for m in models)
        if not models:
            ax.add_patch(Wedge((0, 0), R_CORE, a0, a1, facecolor="#ffffff",
                               edgecolor=C_GRID, hatch="///", linewidth=0.8, zorder=2))
            txt = "no hub\nmodel"
        else:
            frac = cov / tot
            step = min(4, int(frac * 5))
            ax.add_patch(Wedge((0, 0), R_CORE, a0, a1, facecolor=C_HUB_RAMP[step],
                               edgecolor=C_SURF, linewidth=1.5, zorder=2))
            txt = (f"{cov}/{tot}" if FS != 1 else
                   "\n".join(CORE_SHORT[m] for m in models) + f"\n{cov}/{tot}")
        x, y = polar(R_CORE * 0.63, (i + 0.5) * sw)
        ax.text(x, y, txt, ha="center", va="center", fontsize=5.8 * (1 if FS == 1 else FS * 1.1),
                color=C_INK if not models or cov / max(tot, 1) < 0.6 else C_SURF, zorder=3)
    ax.add_patch(Circle((0, 0), R_CORE, facecolor="none", edgecolor=C_HUB, linewidth=1.6, zorder=3))
    ax.text(0, R_CORE + 0.05, "ECCDM hub · 68 elements", ha="center", va="bottom",
            fontsize=7.5 * FS, color=C_INK, fontweight="bold", zorder=4)

    # sector titles on the rim
    for i, (name, _) in enumerate(SECTORS):
        x, y = polar(R_EDGE[-1] + 0.38, (i + 0.5) * sw)
        ax.text(x, y, name, ha="center", va="center", fontsize=10 * FS, fontweight="bold",
                color=C_INK)

    # ring labels: on the vertical top axis (the sectors either side are sparse there)
    for k in range(1, 5):
        ax.text(0, (R_EDGE[k - 1] + R_EDGE[k]) / 2, RING_LABEL[k], ha="center",
                va="center", fontsize=7.2 * FS, color=C_INK2, style="italic", zorder=4,
                linespacing=1.1, bbox=dict(facecolor=C_SURF, edgecolor="none", pad=1.5))

    # bubbles
    nmax = max(n_all.values())
    per_cell = defaultdict(list)
    for cat, (sec, short) in CATEGORY.items():
        if cat not in n_all:
            continue
        per_cell[(sec, RING[carriage[cat]])].append((cat, short))
    for (sec, ring), cats in per_cell.items():
        cats.sort(key=lambda c: -n_all[c[0]])
        r_mid = (R_EDGE[ring - 1] + R_EDGE[ring]) / 2
        k = len(cats)
        # spread angularly inside the sector; bubbles top-aligned at the
        # ring's inner edge so label + source strip fall inside the ring
        radii = [max(0.08, R_MAX_BUBBLE * math.sqrt(n_all[c] / nmax)) for c, _ in cats]
        span_units = sum(2 * r for r in radii) + 0.75 * (k - 1)
        span_deg = math.degrees(span_units / r_mid)
        ang = (sec + 0.5) * sw - span_deg / 2
        for (cat, short), rad in zip(cats, radii):
            ang += math.degrees(rad / r_mid)
            upper = math.cos(math.radians(ang)) > 0.15       # label fits below, inside ring
            r_c = (R_EDGE[ring] - 0.22 - rad) if upper else (R_EDGE[ring - 1] + 0.24 + rad)
            x, y = polar(r_c, ang)
            oos = carriage[cat] == "out-of-scope"
            ax.add_patch(Circle((x, y), max(rad, 0.08),
                                facecolor=C_OOS if oos else C_GENERIC,
                                edgecolor=C_SURF, linewidth=1.5, zorder=5))
            nb = n_breast[cat]
            if nb and not oos:
                rb = rad * math.sqrt(nb / n_all[cat])
                ax.add_patch(Circle((x, y), rb, facecolor=C_BREAST,
                                    edgecolor=C_SURF if rb > 0.1 else "none",
                                    linewidth=1.0, zorder=6))
            # count inside if it fits, else beside
            if rad >= 0.17:
                ax.text(x, y, str(n_all[cat]), ha="center", va="center", fontsize=7.5 * FS,
                        color=C_SURF, fontweight="bold", zorder=7)
            # label + source strip below the bubble
            # label + source strip below the bubble (screen space)
            if rad < 0.17:
                short = short + f" · {n_all[cat]}"
            ly = y - rad - 0.08
            ax.text(x, ly, short, ha="center", va="top", fontsize=6.4 * FS, color=C_INK,
                    zorder=7, linespacing=1.05)
            nlines = short.count("\n") + 1
            sy = ly - 0.17 * nlines - 0.09
            for j, s in enumerate(SRC_ORDER):
                sx = x + (j - 1.5) * 0.14
                on = srcs[cat][s] > 0
                ax.add_patch(plt.Rectangle((sx - 0.055, sy - 0.055), 0.11, 0.11,
                                           facecolor=(C_OOS_IN if oos else fs.SRC_COLOUR[s]) if on else C_SURF,
                                           edgecolor=C_GRID, linewidth=0.6, zorder=7))
            ang += math.degrees((rad + 0.75) / r_mid)

    # legend
    handles = [
        Patch(facecolor=C_HUB_RAMP[3], label="hub core: ECCDM models, shade = coverage by the 4 sources"),
        Patch(facecolor=C_GENERIC, label="pan-cancer content with no hub home"),
        Patch(facecolor=C_BREAST, label="of which breast-cancer-specific (inner disc; lower bound)"),
        Patch(facecolor=C_OOS, label="not clinical cancer content (outside the hub's scope)"),
    ] + [Line2D([], [], marker="s", linestyle="", markersize=7, markerfacecolor=fs.SRC_COLOUR[k],
                markeredgecolor=C_GRID, label=f"strip: {SRC_SHORT[k]} contributes") for k in SRC_ORDER]
    if args.slide:
        ax.set_xlim(-6.8, 6.8); ax.set_ylim(-6.6, 6.6)
        fig.savefig(args.out, dpi=150, bbox_inches="tight", pad_inches=0.1, facecolor=C_SURF)
        print(f"Wrote {args.out}")
        return 0
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=2,
               frameon=False, fontsize=8.5 * FS, handlelength=1.2, columnspacing=1.8)
    ax.set_title("cancer-crosswalk — how far from the ECCDM hub does each kind of "
                 "content sit?\nangle = clinical domain · radius = how ECCDM could "
                 "carry it · area = unmapped source fields",
                 fontsize=12 * FS, fontweight="bold", color=C_INK, pad=14)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches="tight", facecolor=C_SURF)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
