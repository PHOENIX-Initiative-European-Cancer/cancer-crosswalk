#!/usr/bin/env python3
"""Layered target: one circle per source, then the overlay, then the rings.

Same geometry as hub_target.py (angle = clinical domain, radius = carriage),
but drawn as small multiples so each source's profile is visible on its own,
plus an overlay panel where the sources sit on top of each other. INT Breast
is the fifth circle: it is an availability check against ECCDM, so it fills
the core only (its outside content is not inventoried).

Three stages, for a slide build:
  stage 1  the source circles, sectors only (no ring bands)
  stage 2  + the overlay panel
  stage 3  + the distance rings and their labels

Usage:
    python scripts/hub_layers.py [--stage 1|2|3|all|pairs] [--outdir docs]

`--stage pairs` writes hub-layers-pair-{1,2,3}.png: two circles per figure
(oBDS + INT, NABON + B1MG, Senologie + overlay) with slide-sized type.
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
from hub_target import (CATEGORY, R_CORE, R_EDGE, RING, SECTORS, C_GRID, C_INK,  # noqa: E402
                        C_INK2, C_MUTED, C_SURF, polar)
import figstyle as fs  # noqa: E402

REPO = ig.REPO
HUB = REPO / "hub" / "eccdm" / "elements.csv"
INT_XLSX = REPO / "sources" / "int-breast" / "ref" / "INT Breast ECCDM.xlsx"

SRC_COLOUR = fs.SRC_COLOUR
SRC_TITLE = {"mii-onko-obds": "oBDS — DE registry", "nabon-mammacarcinoom": "NABON — NL breast",
             "b1mg-cmd": "B1MG — EU minimal", "senologie-datenkranz": "Senologie — DE breast",
             "int-breast": "INT Milan — breast (hub availability only)"}
C_OOS = fs.OOS
F = {"title": 9.5, "sector": 6.5, "ring": 5.6, "core": 6, "bubble": 6.2, "cat": 4.6, "legend": 8.5, "note": 7}
F_PAIR = {"title": 14, "sector": 10.5, "ring": 8.5, "core": 9.5, "bubble": 9.5, "cat": 7.2, "legend": 12, "note": 10}
R_MAX = 0.45
RING_LABEL = {1: "ring 1 · extend model", 2: "ring 2 · coded finding",
              3: "ring 3 · new module", 4: "outside · not clinical"}


# ------------------------------------------------------------------ data ---
def collect():
    hub_size = Counter()
    model_of = {}
    for r in csv.DictReader(HUB.open(encoding="utf-8")):
        hub_size[r["model"]] += 1
        model_of[r["id"]] = r["model"]
    cov = defaultdict(Counter)         # src -> model -> covered elements
    mapped_subj = defaultdict(set)
    for src in ig.SOURCES:
        f = ig.MAPPINGS / f"{src}__to__eccdm.sssom.tsv"
        seen = set()
        for r in csv.DictReader([l for l in open(f) if not l.startswith("#")], delimiter="\t"):
            if r.get("subject_id"):
                mapped_subj[src].add(r["subject_id"])
            o = r.get("object_id")
            if o in model_of and o not in seen:
                seen.add(o); cov[src][model_of[o]] += 1
    n = defaultdict(Counter)           # category -> src -> fields
    carriage = {}
    for src, path in ig.SOURCES.items():
        for r in ig.load_source(REPO / path):
            if r["id"] in mapped_subj[src]:
                continue
            m, c = ig.classify(r); carriage[m] = c; n[m][src] += 1
    # INT Breast: presence per ECCDM model from the workbook, if present
    int_cov = {}
    if INT_XLSX.exists():
        import openpyxl
        wb = openpyxl.load_workbook(INT_XLSX, data_only=True)
        for ws in wb.worksheets:
            if ws.title not in hub_size:
                continue
            yes = tot = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row[0] or row[0] == "Attribute":
                    continue
                tot += 1
                if str(row[6] or "").strip().lower().startswith("yes"):
                    yes += 1
            int_cov[ws.title] = (yes, tot)
    return hub_size, cov, n, carriage, int_cov


def slots(n, carriage):
    """Fixed (x, y, global_radius) per category, shared by every panel."""
    tot = {m: sum(v.values()) for m, v in n.items()}
    nmax = max(tot.values())
    nsec = len(SECTORS); sw = 360 / nsec
    cell = defaultdict(list)
    for cat, (sec, _) in CATEGORY.items():
        if cat in tot:
            cell[(sec, RING[carriage[cat]])].append(cat)
    pos = {}
    for (sec, ring), cats in cell.items():
        cats.sort(key=lambda c: -tot[c])
        r_mid = (R_EDGE[ring - 1] + R_EDGE[ring]) / 2
        radii = [max(0.08, R_MAX * math.sqrt(tot[c] / nmax)) for c in cats]
        span = sum(2 * r for r in radii) + 0.55 * (len(cats) - 1)
        ang = (sec + 0.5) * sw - math.degrees(span / r_mid) / 2
        for cat, rad in zip(cats, radii):
            ang += math.degrees(rad / r_mid)
            x, y = polar(r_mid, ang)
            pos[cat] = (x, y, rad)
            ang += math.degrees((rad + 0.55) / r_mid)
    nmax_src = max(v for cnt in n.values() for v in cnt.values())
    return pos, nmax_src


# --------------------------------------------------------------- drawing ---
def draw_frame(ax, rings: bool):
    nsec = len(SECTORS); sw = 360 / nsec
    if rings:
        bands = ["#ffffff", fs.BAND, "#ffffff", fs.BAND, fs.BAND2]
        for k in range(1, 5):
            ax.add_patch(Wedge((0, 0), R_EDGE[k], 0, 360, width=R_EDGE[k] - R_EDGE[k - 1],
                               facecolor=bands[k], edgecolor=C_GRID, linewidth=0.7, zorder=0))
    else:
        ax.add_patch(Circle((0, 0), R_EDGE[-1], facecolor="#fbfbfa", edgecolor=C_GRID,
                            linewidth=0.9, zorder=0))
    for i in range(nsec):
        x, y = polar(R_EDGE[-1], i * sw)
        ax.plot([0, x], [0, y], color=C_GRID, linewidth=0.7, zorder=1)
    for i, (name, _) in enumerate(SECTORS):
        x, y = polar(R_EDGE[-1] + 0.55, (i + 0.5) * sw)
        ax.text(x, y, name.replace("\n", " "), ha="center", va="center", fontsize=F["sector"],
                color=C_INK2, zorder=4)
    if rings:
        for k in range(1, 5):
            ax.text(0, (R_EDGE[k - 1] + R_EDGE[k]) / 2, RING_LABEL[k], ha="center",
                    va="center", fontsize=F["ring"], style="italic", color=C_INK2, zorder=4,
                    bbox=dict(facecolor=C_SURF, edgecolor="none", pad=1))


def draw_core(ax, hub_size, covered, colour, label=None):
    """Core wedges: alpha by coverage of that sector's models."""
    nsec = len(SECTORS); sw = 360 / nsec
    for i, (name, models) in enumerate(SECTORS):
        a0, a1 = 90 - (i + 1) * sw, 90 - i * sw
        tot = sum(hub_size[m] for m in models)
        if not tot:
            ax.add_patch(Wedge((0, 0), R_CORE, a0, a1, facecolor="#ffffff", edgecolor=C_GRID,
                               hatch="////", linewidth=0.6, zorder=2))
            continue
        cov = sum(covered.get(m, 0) for m in models)
        frac = cov / tot
        ax.add_patch(Wedge((0, 0), R_CORE, a0, a1, facecolor=colour,
                           alpha=0.15 + 0.85 * frac, edgecolor=C_SURF, linewidth=1.2, zorder=2))
        x, y = polar(R_CORE * 0.6, (i + 0.5) * sw)
        ax.text(x, y, f"{cov}/{tot}", ha="center", va="center", fontsize=F["core"],
                color=C_INK if frac < 0.55 else C_SURF, zorder=3)
    ax.add_patch(Circle((0, 0), R_CORE, facecolor="none", edgecolor=C_INK2, linewidth=1.0, zorder=3))
    if label:
        ax.text(0, -R_CORE - 0.12, label, ha="center", va="top", fontsize=F["core"], color=C_INK2)


def draw_bubbles(ax, n, carriage, pos, nmax, src, alpha=1.0, labels=False):
    items = sorted(pos.items(), key=lambda kv: -n[kv[0]][src])
    for cat, (x, y, _) in items:
        k = n[cat][src]
        if not k:
            continue
        rad = max(0.08, R_MAX * math.sqrt(k / nmax))
        oos = carriage[cat] == "out-of-scope"
        ax.add_patch(Circle((x, y), rad, facecolor=C_OOS if oos else SRC_COLOUR[src],
                            alpha=alpha, edgecolor=C_SURF, linewidth=0.8, zorder=5))
        if rad >= 0.19 and alpha == 1.0:
            ax.text(x, y, str(k), ha="center", va="center", fontsize=F["bubble"], color=C_SURF,
                    fontweight="bold", zorder=7)
    if labels:
        for cat, (x, y, rad) in pos.items():
            ax.text(x, y - rad - 0.05, CATEGORY[cat][1], ha="center", va="top", fontsize=F["cat"],
                    color=C_INK, zorder=8, linespacing=1.0)


def panel(ax, title, colour):
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(-6.9, 6.9); ax.set_ylim(-6.9, 6.9)
    ax.set_title(title, fontsize=F["title"], fontweight="bold", color=colour, pad=4)


def render(stage: int, out: Path, data):
    hub_size, cov, n, carriage, int_cov = data
    pos, nmax = slots(n, carriage)
    srcs = list(ig.SOURCES) + (["int-breast"] if int_cov else [])
    rings = stage >= 3
    fig, axes = plt.subplots(2, 3, figsize=(19, 13), facecolor=C_SURF)
    axes = axes.ravel()
    for ax, src in zip(axes, srcs):
        panel(ax, SRC_TITLE[src], C_INK)
        draw_frame(ax, rings)
        if src == "int-breast":
            covered = {m: y for m, (y, t) in int_cov.items()}
            size = Counter({m: t for m, (y, t) in int_cov.items()}) or hub_size
            draw_core(ax, size, covered, SRC_COLOUR[src])
            ax.set_title(f"{SRC_TITLE[src]}  ·  {sum(covered.values())} / {sum(size.values())} attributes present",
                         fontsize=F["title"], fontweight="bold", color=C_INK, pad=4)
            ax.text(0, -3.4, "outside content\nnot inventoried", ha="center", va="center",
                    fontsize=F["note"], color=C_MUTED, style="italic")
        else:
            ax.set_title(f"{SRC_TITLE[src]}  ·  {sum(cov[src].values())} / 68 hub elements",
                         fontsize=F["title"], fontweight="bold", color=C_INK, pad=4)
            draw_core(ax, hub_size, cov[src], SRC_COLOUR[src])
            draw_bubbles(ax, n, carriage, pos, nmax, src)
    # overlay
    ax = axes[len(srcs)] if len(srcs) < 6 else axes[5]
    if stage >= 2:
        panel(ax, "Overlay — all sources on the same grid", C_INK)
        draw_frame(ax, rings)
        union = Counter()
        for src in ig.SOURCES:
            for m, v in cov[src].items():
                union[m] = max(union[m], v)
        ax.set_title(f"Overlay — all sources on the same grid  ·  core = best coverage per model",
                     fontsize=F["title"], fontweight="bold", color=C_INK, pad=4)
        draw_core(ax, hub_size, union, fs.OOS_DARK)
        for src in ig.SOURCES:
            draw_bubbles(ax, n, carriage, pos, nmax, src, alpha=0.5)
        for cat, (x, y, rad) in pos.items():
            ax.text(x, y - rad - 0.05, CATEGORY[cat][1], ha="center", va="top", fontsize=F["cat"],
                    color=C_INK, zorder=8, linespacing=1.0)
    else:
        ax.axis("off")
    handles = [Patch(facecolor=SRC_COLOUR[s], label=SRC_TITLE[s].split(" — ")[0]) for s in srcs]
    handles.append(Patch(facecolor=C_OOS, label="not clinical cancer content (any source)"))
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), frameon=False,
               fontsize=F["legend"], bbox_to_anchor=(0.5, 0.01))
    sub = {1: "one circle per source · angle = clinical domain · core = ECCDM models, shade = hub coverage · bubble area = fields with no hub home",
           2: "stage 2 · the overlay shows where the sources coincide",
           3: "stage 3 · radius = how ECCDM could carry the content: extend a model · coded finding · new module · outside"}[stage]
    fig.suptitle(f"cancer-crosswalk — sources as layers over the ECCDM hub\n{sub}",
                 fontsize=13, fontweight="bold", y=0.985)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.07, wspace=0.05, hspace=0.12)
    fig.savefig(out, dpi=150, facecolor=C_SURF)
    plt.close(fig)
    print(f"Wrote {out}")


def draw_source_panel(ax, src, data, pos, nmax, rings):
    hub_size, cov, n, carriage, int_cov = data
    panel(ax, SRC_TITLE[src], C_INK)
    draw_frame(ax, rings)
    if src == "int-breast":
        # ActiveSurveillance is not applicable to breast cancer: INT counts 62 of 68 applicable
        covered = {m: y for m, (y, t) in int_cov.items() if m != "ActiveSurveillance"}
        size = Counter({m: t for m, (y, t) in int_cov.items() if m != "ActiveSurveillance"}) or hub_size
        draw_core(ax, size, covered, SRC_COLOUR[src])
        short = SRC_TITLE[src].split(" (")[0]
        ax.set_title(f"{short}  ·  {sum(covered.values())} / {sum(size.values())} applicable attributes present",
                     fontsize=F["title"], fontweight="bold", color=C_INK, pad=4)
        ax.text(0, -3.4, "outside content\nnot inventoried", ha="center", va="center",
                fontsize=F["note"], color=C_MUTED, style="italic")
    else:
        ax.set_title(f"{SRC_TITLE[src]}  ·  {sum(cov[src].values())} / 68 hub elements",
                     fontsize=F["title"], fontweight="bold", color=C_INK, pad=4)
        draw_core(ax, hub_size, cov[src], SRC_COLOUR[src])
        draw_bubbles(ax, n, carriage, pos, nmax, src)


def draw_overlay_panel(ax, data, pos, nmax, rings):
    hub_size, cov, n, carriage, _ = data
    panel(ax, "Overlay", C_INK)
    draw_frame(ax, rings)
    model_of = {r["id"]: r["model"] for r in csv.DictReader(HUB.open(encoding="utf-8"))}
    reached = defaultdict(set)
    for src in ig.SOURCES:
        f = ig.MAPPINGS / f"{src}__to__eccdm.sssom.tsv"
        for r in csv.DictReader([l for l in open(f) if not l.startswith("#")], delimiter="\t"):
            o = r.get("object_id")
            if o in model_of:
                reached[model_of[o]].add(o)
    union = Counter({m: len(v) for m, v in reached.items()})
    ax.set_title(f"Overlay — all sources  ·  core = elements reached by any source  ·  {sum(union.values())} / 68",
                 fontsize=F["title"], fontweight="bold", color=C_INK, pad=4)
    draw_core(ax, hub_size, union, fs.OOS_DARK)
    for src in ig.SOURCES:
        draw_bubbles(ax, n, carriage, pos, nmax, src, alpha=0.5)
    for cat, (x, y, rad) in pos.items():
        ax.text(x, y - rad - 0.05, CATEGORY[cat][1], ha="center", va="top", fontsize=F["cat"],
                color=C_INK, zorder=8, linespacing=1.0)


PAIRS = [("mii-onko-obds", "int-breast"), ("nabon-mammacarcinoom", "b1mg-cmd"),
         ("senologie-datenkranz", "overlay")]


def render_pairs(outdir: Path, data):
    """Slide version: two circles per figure (three figures), large type, no suptitle."""
    global F
    saved, F = F, F_PAIR
    hub_size, cov, n, carriage, int_cov = data
    pos, nmax = slots(n, carriage)
    for k, pair in enumerate(PAIRS, 1):
        fig, axes = plt.subplots(1, 2, figsize=(17, 8.6), facecolor=C_SURF)
        for ax, src in zip(axes, pair):
            if src == "overlay":
                draw_overlay_panel(ax, data, pos, nmax, rings=True)
            else:
                draw_source_panel(ax, src, data, pos, nmax, rings=True)
        srcs = [s for s in pair if s != "overlay"]
        if "overlay" in pair:
            srcs = list(ig.SOURCES)
        handles = [Patch(facecolor=SRC_COLOUR[s], label=SRC_TITLE[s].split(" — ")[0]) for s in srcs]
        handles.append(Patch(facecolor=C_OOS, label="not clinical cancer content"))
        fig.legend(handles=handles, loc="lower center", ncol=len(handles), frameon=False,
                   fontsize=F["legend"], bbox_to_anchor=(0.5, 0.005))
        fig.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.07, wspace=0.04)
        out = outdir / f"hub-layers-pair-{k}.png"
        fig.savefig(out, dpi=150, facecolor=C_SURF)
        plt.close(fig)
        print(f"Wrote {out}")
    F = saved


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", default="all", help="1|2|3|all, or 'pairs' for the two-per-slide figures")
    ap.add_argument("--outdir", type=Path, default=REPO / "docs")
    args = ap.parse_args()
    fs.apply()
    data = collect()
    if args.stage == "pairs":
        render_pairs(args.outdir, data)
        return 0
    stages = [1, 2, 3] if args.stage == "all" else [int(args.stage)]
    for s in stages:
        render(s, args.outdir / f"hub-layers-{s}.png", data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
