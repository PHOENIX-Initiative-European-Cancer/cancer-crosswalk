#!/usr/bin/env python3
"""Two-sided overview figure — the readable, WG-facing picture.

Panel A (top): model-level hub coverage — 11 ECCDM models x 4 sources, cell
  shaded by coverage fraction (hub elements of that model mapped by the source),
  annotated m/n, tinted by the source's dominant predicate for that model.

Panel B (bottom): Extension modules — the breast-specific / detailed content
  that has NO hub home, as stacked bars per candidate extension module, coloured
  by carriage (by-reference / new-module). Shows the hub is a thin generic spine
  while the specialised detail forms fat extension modules.

Reads hub/eccdm/elements.csv, mappings/*.sssom.tsv, and reuses the clustering
from inverse_gaps.py.

Usage:
    python scripts/overview.py [--out docs/overview.png]
"""
from __future__ import annotations

import argparse
import csv
import glob
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

import inverse_gaps as ig  # reuse SOURCES, classify(), load_source()
import figstyle as fs

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
HUB = REPO / "hub" / "eccdm" / "elements.csv"
MAPPINGS = REPO / "mappings"
DEFAULT_OUT = REPO / "docs" / "overview.png"

SRC_SHORT = {"b1mg-cmd": "B1MG", "mii-onko-obds": "oBDS",
             "nabon-mammacarcinoom": "NABON", "senologie-datenkranz": "Senologie"}
CARR_COLOR = fs.CARRIAGE_COLOUR
FS = 1.0                                     # font scale, raised in --slide mode


def read_sssom(path: Path):
    lines = [l for l in path.read_text(encoding="utf-8").splitlines()
             if not l.startswith("#")]
    return list(csv.DictReader(lines, delimiter="\t")) if lines else []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--slide", action="store_true",
                    help="slide version: panels side by side, no figure title, larger type")
    args = ap.parse_args()
    global FS
    FS = 1.35 if args.slide else 1.0
    fs.apply()
    if args.slide and args.out == DEFAULT_OUT:
        args.out = DEFAULT_OUT.with_name("overview-slide.png")

    hub = list(csv.DictReader(HUB.open(encoding="utf-8")))
    models = []
    size = Counter()
    for r in hub:
        if r["model"] not in size:
            models.append(r["model"])
        size[r["model"]] += 1

    srcs = list(ig.SOURCES.keys())
    # (model, src) -> set(covered hub element ids), and predicate counter
    covered = defaultdict(set)
    preds = defaultdict(Counter)
    for f in sorted(glob.glob(str(MAPPINGS / "*__to__eccdm.sssom.tsv"))):
        src = Path(f).name.split("__to__")[0]
        for row in read_sssom(Path(f)):
            obj = row.get("object_id")
            if not obj:
                continue
            model = obj.split(".")[0].split(":")[1]
            covered[(model, src)].add(obj)
            if row.get("predicate_id"):
                preds[(model, src)][row["predicate_id"]] += 1

    # Extension modules (reuse inverse_gaps clustering)
    mapped = {row["subject_id"] for f in glob.glob(str(MAPPINGS / "*.sssom.tsv"))
              for row in read_sssom(Path(f)) if row.get("subject_id")}
    mod_src = defaultdict(lambda: defaultdict(int))
    mod_carr = {}
    for src, path in ig.SOURCES.items():
        for r in ig.load_source(REPO / path):
            if r["id"] in mapped:
                continue
            m, c = ig.classify(r)
            if c in ("by-reference", "extend-model", "new-module"):   # clinical only
                mod_src[m][src] += 1
                mod_carr[m] = c

    if args.slide:
        fig = plt.figure(figsize=(18, 8.4))
        gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.5], wspace=1.05,
                              left=0.145, right=0.985, top=0.86, bottom=0.11)
    else:
        fig = plt.figure(figsize=(13, 12))
        gs = fig.add_gridspec(2, 1, height_ratios=[len(models), max(6, len(mod_src))],
                              hspace=0.28)

    # ---- Panel A: model x source coverage ----
    axA = fig.add_subplot(gs[0])
    nrows, ncols = len(models), len(srcs)
    for i, model in enumerate(models):
        for j, src in enumerate(srcs):
            cov = covered[(model, src)]
            frac = len(cov) / size[model]
            if cov:
                step = min(4, 1 + int(frac * 4))          # one hue, light -> dark
                rgba = fs.HUB_RAMP[step]
                txt = f"{len(cov)}/{size[model]}"
                tcol = fs.SURF if step >= 3 else fs.INK
            else:
                rgba = fs.HUB_RAMP[0]
                txt, tcol = "·", fs.MUTED
            axA.add_patch(plt.Rectangle((j, nrows - 1 - i), 1, 1, facecolor=rgba,
                                        edgecolor=fs.SURF, lw=2))
            axA.text(j + 0.5, nrows - 1 - i + 0.5, txt, ha="center", va="center",
                     fontsize=8 * FS, color=tcol)
    axA.set_xlim(0, ncols); axA.set_ylim(0, nrows)
    axA.set_xticks([j + 0.5 for j in range(ncols)])
    axA.set_xticklabels([SRC_SHORT[s] for s in srcs], fontsize=9 * FS)
    axA.xaxis.tick_top()
    axA.set_yticks([nrows - 1 - i + 0.5 for i in range(nrows)])
    axA.set_yticklabels(models, fontsize=8 * FS)
    axA.tick_params(length=0)
    for sp in axA.spines.values():
        sp.set_visible(False)
    axA.set_title("A · Hub coverage per ECCDM model\n(elements mapped / model size, darker = more)",
                  fontsize=10 * FS, pad=26 * FS, loc="left", color=fs.INK)
    cov_legend = [Patch(facecolor=fs.HUB_RAMP[k], label=lbl)
                  for k, lbl in [(4, "high"), (2, "mid"), (1, "low"), (0, "none")]]
    axA.legend(handles=cov_legend, loc="upper left", bbox_to_anchor=(0, -0.02), ncol=4,
               fontsize=7.5 * FS, frameon=False, handlelength=1.2, columnspacing=1.2)

    # ---- Panel B: Extension modules ----
    axB = fig.add_subplot(gs[1])
    order = sorted(mod_src, key=lambda m: sum(mod_src[m].values()))
    for i, m in enumerate(order):
        left = 0
        for src in srcs:
            v = mod_src[m].get(src, 0)
            if v:
                axB.barh(i, v, left=left, height=0.62, facecolor=fs.SRC_COLOUR[src],
                         edgecolor=fs.SURF, linewidth=1.5)
                if v >= 9:                                  # label only where it fits
                    axB.text(left + v / 2, i, str(v), ha="center", va="center",
                             fontsize=7 * FS, color=fs.SURF)
                left += v
        axB.text(left + 1.5, i, mod_carr[m], va="center", fontsize=7 * FS,
                 color=fs.INK2, style="italic")
    axB.set_yticks(range(len(order)))
    axB.set_yticklabels(order, fontsize=8.5 * FS)
    axB.set_xlabel("source fields with no hub home", fontsize=8.5 * FS)
    axB.set_xlim(0, max(sum(mod_src[m].values()) for m in order) * 1.22)
    axB.tick_params(length=0, labelsize=8 * FS)
    axB.xaxis.grid(True, color=fs.GRID, linewidth=0.8); axB.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        axB.spines[sp].set_visible(False)
    axB.spines["bottom"].set_color(fs.GRID)
    axB.set_title("B · Content the generic hub cannot hold, by category\n"
                  "(stack = source; tag = how ECCDM could carry it)",
                  fontsize=10 * FS, pad=8 * FS, loc="left", color=fs.INK)
    axB.legend(handles=[Patch(facecolor=fs.SRC_COLOUR[s_], label=SRC_SHORT[s_]) for s_ in srcs],
               loc="lower right", frameon=False, fontsize=7.5 * FS, handlelength=1.2)
    axB.text(1.0, -0.1 if args.slide else -0.14, "out-of-scope fields (admin, registry transport, "
             "other-entity modules, biobank infrastructure) omitted",
             transform=axB.transAxes, ha="right", fontsize=7 * FS, color=fs.MUTED)

    if not args.slide:
        fig.suptitle("cancer-crosswalk — generic ECCDM spine (A) vs breast-specific "
                     "extension need (B)", fontsize=13 * FS, fontweight="bold", y=0.995)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches=None if args.slide else "tight")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
