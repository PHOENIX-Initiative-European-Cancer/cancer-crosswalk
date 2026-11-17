#!/usr/bin/env python3
"""What lies OUTSIDE the ECCDM hub — per source, and shared by whom.

Two panels:

  A · For each source: how much of its vocabulary has a hub home (inside) vs
      none (outside), the outside split into clinical extension candidates,
      administrative / infrastructure (out of scope) and not-yet-triaged.
      100 %-stacked horizontal bars, one per source, so the sources compare on
      one axis.

  B · The outside content as a source x theme matrix: dot area = number of
      fields, dot colour = how ECCDM could carry the theme. The right-hand
      column counts how many sources share the theme — this is the "Venn"
      question (what do the sources have in common outside the hub?) answered
      without a Venn, which is unreadable past three sets.

Reads sources/*/elements.csv + mappings/*__to__eccdm.sssom.tsv and reuses the
clustering from inverse_gaps.py. Writes docs/outside-hub.png.

Usage:
    python scripts/outside_hub.py [--out docs/outside-hub.png]
"""
from __future__ import annotations

import argparse
import csv
import glob
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from inverse_gaps import MAPPINGS, REPO, SOURCES, classify, load_source  # noqa: E402
import figstyle as fs  # noqa: E402

DEFAULT_OUT = REPO / "docs" / "outside-hub.png"

SRC_LABEL = {
    "mii-onko-obds": "oBDS (DE registry)",
    "nabon-mammacarcinoom": "NABON (NL breast)",
    "b1mg-cmd": "B1MG (EU minimal)",
    "senologie-datenkranz": "Senologie (DE breast)",
}

# colour by *job*: inside the hub = blue; outside, clinical and attachable =
# orange; the rest is de-emphasis grey (two steps).
C_INSIDE = fs.HUB
C_EXT = fs.GENERIC
C_OOS = fs.OOS
C_TRIAGE = fs.BAND2
C_INK = fs.INK
C_INK2 = fs.INK2
C_MUTED = fs.MUTED
C_GRID = fs.GRID
C_SURF = fs.SURF
FS = 1.0                                     # font scale, raised in --slide mode
CARRIAGE_COLOUR = {"by-reference": C_EXT, "extend-model": C_EXT, "new-module": C_EXT,
                   "out-of-scope": C_OOS, "review": C_TRIAGE}
CARRIAGE_LABEL = {
    "by-reference": "clinical content with no hub home",
    "out-of-scope": "not clinical cancer content — out of scope for ECCDM",
}
CARRIAGE_SHORT = {"by-reference": "by reference", "extend-model": "extend model",
                  "new-module": "new module", "out-of-scope": "out of scope",
                  "review": "review"}


def collect():
    mapped = set()
    for f in glob.glob(str(MAPPINGS / "*__to__eccdm.sssom.tsv")):
        rows = csv.DictReader([l for l in open(f) if not l.startswith("#")],
                              delimiter="\t")
        for r in rows:
            if r.get("subject_id"):
                mapped.add(r["subject_id"])

    share = {}                      # src -> Counter(inside/ext/oos/triage)
    matrix = defaultdict(Counter)   # theme -> Counter(src -> n)
    carriage = {}
    for src, path in SOURCES.items():
        c = Counter()
        for r in load_source(REPO / path):
            if r["id"] in mapped:
                c["inside"] += 1
                continue
            theme, carr = classify(r)
            carriage[theme] = carr
            matrix[theme][src] += 1
            if carr in ("by-reference", "extend-model", "new-module"):
                c["ext"] += 1
            elif carr == "out-of-scope":
                c["oos"] += 1
            else:
                c["triage"] += 1
        share[src] = c
    return share, matrix, carriage


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--slide", action="store_true",
                    help="slide version: A left, B right, no figure title, larger type")
    args = ap.parse_args()
    global FS
    FS = 1.4 if args.slide else 1.0
    fs.apply()
    if args.slide and args.out == DEFAULT_OUT:
        args.out = DEFAULT_OUT.with_name("outside-hub-slide.png")

    share, matrix, carriage = collect()
    srcs = list(SOURCES)

    if args.slide:
        fig = plt.figure(figsize=(18, 8.6), facecolor=C_SURF)
        gs = fig.add_gridspec(2, 2, width_ratios=[0.85, 1.65], height_ratios=[1, 1.4],
                              wspace=0.95, hspace=0.9, left=0.11, right=0.99, top=0.86, bottom=0.04)
        axA = fig.add_subplot(gs[0, 0])
        axB = fig.add_subplot(gs[:, 1])
    else:
        fig = plt.figure(figsize=(13, 11.5), facecolor=C_SURF)
        gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 2.6], hspace=0.45)
        axA = fig.add_subplot(gs[0])
        axB = fig.add_subplot(gs[1])

    # ---------------- A · inside vs outside, 100 % stacked ----------------
    segs = [("inside", C_INSIDE, "inside the hub (mapped to ECCDM)"),
            ("ext", C_EXT, "outside — clinical content ECCDM would need"),
            ("oos", C_OOS, "outside — not clinical cancer content" + ("" if args.slide else " (admin, transport, other entities)")),
            ("triage", C_TRIAGE, "outside — not yet triaged")]
    gap = 0.4   # % of width, drawn in surface colour
    for i, src in enumerate(srcs):
        tot = sum(share[src].values())
        left = 0.0
        for key, col, _ in segs:
            pct = 100 * share[src][key] / tot
            if pct == 0:
                continue
            axA.barh(i, pct, left=left, height=0.55, color=col,
                     edgecolor=C_SURF, linewidth=1.5)
            if pct >= 6 * FS * FS:                       # label only where it fits
                tcol = C_SURF if key in ("inside", "ext", "oos") else C_INK
                axA.text(left + pct / 2, i, f"{pct:.0f} %", ha="center",
                         va="center", fontsize=8 * FS, color=tcol,
                         fontweight="bold" if key == "inside" else "normal")
            left += pct
        axA.text(101, i, f"n = {tot}", va="center", fontsize=8 * FS, color=C_INK2)
    axA.set_yticks(range(len(srcs)))
    axA.set_yticklabels([SRC_LABEL[s] for s in srcs], fontsize=9 * FS)
    axA.invert_yaxis()
    axA.set_xlim(0, 112)
    axA.set_xticks([0, 25, 50, 75, 100])
    axA.set_xticklabels(["0", "25", "50", "75", "100 %"], fontsize=8 * FS)
    axA.xaxis.grid(True, color=C_GRID, linewidth=0.8)
    axA.set_axisbelow(True)
    for s in ("top", "right", "left"):
        axA.spines[s].set_visible(False)
    axA.spines["bottom"].set_color(C_GRID)
    axA.tick_params(length=0)
    axA.set_title("A · Share of each source with a home in ECCDM\n(dark) — and what the rest is",
                  fontsize=10 * FS, loc="left", pad=12 * FS, color=C_INK)
    used = {k for s in srcs for k, v in share[s].items() if v}
    axA.legend(handles=[Patch(facecolor=c, label=l) for k, c, l in segs if k in used],
               loc="upper left", bbox_to_anchor=(-0.02, -0.22 if not args.slide else -0.3),
               ncol=2 if not args.slide else 1,
               frameon=False, fontsize=8 * FS, handlelength=1.2, columnspacing=1.6)

    # ---------------- B · outside content: source x theme dot matrix ----------
    themes = [t for t in matrix if carriage[t] != "review"]
    rank = {"by-reference": 0, "extend-model": 1, "new-module": 2, "out-of-scope": 3}
    themes.sort(key=lambda t: (rank[carriage[t]], -sum(matrix[t].values())))
    nmax = max(matrix[t][s] for t in themes for s in srcs)
    smax = 1050   # pt² for the largest dot

    for j, src in enumerate(srcs):
        axB.axvline(j, color=C_GRID, linewidth=0.8, zorder=0)
    for i, t in enumerate(themes):
        axB.axhline(i, color=C_GRID, linewidth=0.8, zorder=0)
        col = CARRIAGE_COLOUR[carriage[t]]
        for j, src in enumerate(srcs):
            n = matrix[t][src]
            if n == 0:
                axB.scatter(j, i, s=14, facecolor=C_SURF, edgecolor=C_GRID,
                            linewidth=0.8, zorder=2)
                continue
            axB.scatter(j, i, s=max(40, smax * n / nmax), color=col, zorder=3,
                        edgecolor=C_SURF, linewidth=2)
            if n / nmax >= 0.22:
                axB.text(j, i, str(n), ha="center", va="center", fontsize=7.5 * FS,
                         color=C_SURF, zorder=4, fontweight="bold")
            else:
                axB.text(j + 0.1, i, str(n), ha="left", va="center",
                         fontsize=7.5 * FS, color=C_INK2, zorder=4)
        shared = sum(1 for s in srcs if matrix[t][s])
        tot = sum(matrix[t].values())
        axB.text(len(srcs) - 0.3, i, f"{shared} / 4", ha="left", va="center",
                 fontsize=8.5 * FS, color=C_INK, fontweight="bold")
        axB.text(len(srcs) + 0.45, i, f"{tot}", ha="left", va="center",
                 fontsize=8 * FS, color=C_INK2)
        axB.text(len(srcs) + 1.05, i, CARRIAGE_SHORT[carriage[t]], ha="left",
                 va="center", fontsize=8 * FS, color=C_INK2, style="italic")

    axB.set_xlim(-0.6, len(srcs) + 2.1)
    axB.set_ylim(len(themes) - 0.5, -0.5)
    axB.set_xticks(range(len(srcs)))
    axB.set_xticklabels([SRC_LABEL[s].replace(" (", "\n(") for s in srcs],
                        fontsize=8.5 * FS)
    axB.xaxis.tick_top()
    axB.set_yticks(range(len(themes)))
    axB.set_yticklabels([t.split(" (")[0] if args.slide else t for t in themes], fontsize=9 * FS)
    axB.text(len(srcs) - 0.3, -1.0, "shared\nby", ha="left", va="center",
             fontsize=8.5 * FS, color=C_INK2, fontweight="bold")
    axB.text(len(srcs) + 0.45, -1.0, "fields", ha="left", va="center",
             fontsize=8.5 * FS, color=C_INK2, fontweight="bold")
    axB.text(len(srcs) + 1.05, -1.0, "how ECCDM\ncould carry it", ha="left",
             va="center", fontsize=8.5 * FS, color=C_INK2, fontweight="bold")
    for s in axB.spines.values():
        s.set_visible(False)
    axB.tick_params(length=0)
    axB.set_title("B · What the outside content is, and which sources share it\n"
                  "(dot area = fields with no hub home)", fontsize=10 * FS,
                  loc="left", pad=40 * FS, color=C_INK)

    handles = [Line2D([], [], marker="o", linestyle="", markersize=9,
                      color=CARRIAGE_COLOUR[k], label=CARRIAGE_LABEL[k])
               for k in ("by-reference", "out-of-scope")]
    if args.slide:
        axA.legend(handles=[Patch(facecolor=c, label=l) for k, c, l in segs if k in used] + handles,
                   loc="upper left", bbox_to_anchor=(-0.02, -0.3), ncol=1, frameon=False,
                   fontsize=8 * FS, handlelength=1.2, labelspacing=0.9)
    else:
        axB.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.45, -0.04),
                   ncol=2, frameon=False, fontsize=8 * FS, handletextpad=0.4,
                   columnspacing=1.6)
    n_rev = sum(sum(matrix[t].values()) for t in matrix if carriage[t] == "review")
    note = (f"not shown: {n_rev} fields still under review; " if n_rev else "")
    axB.text(1.0, -0.13, note + "field lists per category in docs/extension-modules.md",
             transform=axB.transAxes, ha="right", fontsize=7 * FS, color=C_MUTED)

    if not args.slide:
        fig.suptitle("cancer-crosswalk — what lies outside the ECCDM hub",
                     fontsize=13 * FS, fontweight="bold", y=0.985, color=C_INK)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches=None if args.slide else "tight", facecolor=C_SURF)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
