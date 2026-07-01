#!/usr/bin/env python3
"""Two-sided overview figure — the readable, WG-facing picture.

Panel A (top): model-level hub coverage — 11 ECCDM models x 4 sources, cell
  shaded by coverage fraction (hub elements of that model mapped by the source),
  annotated m/n, tinted by the source's dominant predicate for that model.

Panel B (bottom): Ergaenzungsmodule — the breast-specific / detailed content
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
import matplotlib.colors as mcolors
from matplotlib.patches import Patch

import inverse_gaps as ig  # reuse SOURCES, classify(), load_source()

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
HUB = REPO / "hub" / "eccdm" / "elements.csv"
MAPPINGS = REPO / "mappings"
DEFAULT_OUT = REPO / "docs" / "overview.png"

PRED = {"skos:exactMatch": "#1a7d3c", "skos:closeMatch": "#7cb342",
        "skos:narrowMatch": "#4a90d9", "skos:broadMatch": "#f5a623",
        "skos:relatedMatch": "#b39ddb"}
SRC_SHORT = {"b1mg-cmd": "B1MG", "mii-onko-obds": "oBDS",
             "nabon-mammacarcinoom": "NABON", "senologie-datenkranz": "Senologie"}
CARR_COLOR = {"by-reference": "#4a90d9", "new-module": "#e0662b",
              "out-of-scope": "#c9ccd1", "review": "#e8e2b0"}


def read_sssom(path: Path):
    lines = [l for l in path.read_text(encoding="utf-8").splitlines()
             if not l.startswith("#")]
    return list(csv.DictReader(lines, delimiter="\t")) if lines else []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

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

    # Ergaenzungsmodule (reuse inverse_gaps clustering)
    mapped = {row["subject_id"] for f in glob.glob(str(MAPPINGS / "*.sssom.tsv"))
              for row in read_sssom(Path(f)) if row.get("subject_id")}
    mod_src = defaultdict(lambda: defaultdict(int))
    mod_carr = {}
    for src, path in ig.SOURCES.items():
        for r in ig.load_source(REPO / path):
            if r["id"] in mapped:
                continue
            m, c = ig.classify(r["_text"])
            if c in ("by-reference", "new-module"):   # clinical extension need only
                mod_src[m][src] += 1
                mod_carr[m] = c

    fig = plt.figure(figsize=(13, 12))
    gs = fig.add_gridspec(2, 1, height_ratios=[len(models), max(6, len(mod_src))],
                          hspace=0.28)

    # ---- Panel A: model x source coverage ----
    axA = fig.add_subplot(gs[0])
    nrows, ncols = len(models), len(srcs)
    COVER_HUE = "#2c7fb8"   # single hue; intensity = coverage fraction only
    for i, model in enumerate(models):
        for j, src in enumerate(srcs):
            cov = covered[(model, src)]
            frac = len(cov) / size[model]
            if cov:
                rgba = mcolors.to_rgba(COVER_HUE, alpha=0.18 + 0.72 * frac)
                txt = f"{len(cov)}/{size[model]}"
                tcol = "white" if frac > 0.55 else "#1a1a1a"
            else:
                rgba = mcolors.to_rgba("#ececec", 1)
                txt, tcol = "·", "#999"
            axA.add_patch(plt.Rectangle((j, nrows - 1 - i), 1, 1, facecolor=rgba,
                                        edgecolor="white", lw=1.2))
            axA.text(j + 0.5, nrows - 1 - i + 0.5, txt, ha="center", va="center",
                     fontsize=8, color=tcol)
    axA.set_xlim(0, ncols); axA.set_ylim(0, nrows)
    axA.set_xticks([j + 0.5 for j in range(ncols)])
    axA.set_xticklabels([SRC_SHORT[s] for s in srcs], fontsize=9)
    axA.xaxis.tick_top()
    axA.set_yticks([nrows - 1 - i + 0.5 for i in range(nrows)])
    axA.set_yticklabels(models, fontsize=8)
    axA.tick_params(length=0)
    for sp in axA.spines.values():
        sp.set_visible(False)
    axA.set_title("A · Hub coverage per ECCDM model  (cell = elements mapped / "
                  "model size; darker = higher coverage)", fontsize=10, pad=26)
    cov_legend = [Patch(facecolor=mcolors.to_rgba("#2c7fb8", a), label=lbl)
                  for a, lbl in [(0.9, "high"), (0.5, "mid"), (0.2, "low")]] + \
                 [Patch(facecolor="#ececec", label="gap")]
    axA.legend(handles=cov_legend, loc="upper left", bbox_to_anchor=(1.01, 1),
               fontsize=7.5, frameon=False, title="coverage")

    # ---- Panel B: Ergaenzungsmodule ----
    axB = fig.add_subplot(gs[1])
    order = sorted(mod_src, key=lambda m: sum(mod_src[m].values()))
    for i, m in enumerate(order):
        left = 0
        for src in srcs:
            v = mod_src[m].get(src, 0)
            if v:
                axB.barh(i, v, left=left, height=0.6,
                         facecolor=CARR_COLOR[mod_carr[m]],
                         edgecolor="white", alpha=0.55 + 0.11 * srcs.index(src))
                axB.text(left + v / 2, i, str(v), ha="center", va="center",
                         fontsize=7, color="white")
                left += v
        axB.text(left + 1, i, f"  {mod_carr[m]}", va="center", fontsize=7,
                 color=CARR_COLOR[mod_carr[m]])
    axB.set_yticks(range(len(order)))
    axB.set_yticklabels(order, fontsize=8.5)
    axB.set_xlabel("source fields with NO hub home (breast-specific / detailed)")
    axB.tick_params(length=0)
    for sp in ("top", "right"):
        axB.spines[sp].set_visible(False)
    axB.set_title("B · Ergaenzungsmodule — content the generic hub can't hold "
                  "(→ attach by evidence-reference / new module)", fontsize=10, pad=8)
    axB.text(0.99, -0.14, "shading within a bar = the 4 sources; "
             "out-of-scope (admin/biobank) and unclustered fields omitted",
             transform=axB.transAxes, ha="right", fontsize=7, color="#888")

    fig.suptitle("cancer-crosswalk — generic ECCDM spine (A) vs breast-specific "
                 "extension need (B)", fontsize=13, fontweight="bold", y=0.995)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches="tight")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
