#!/usr/bin/env python3
"""Coverage heatmap: ECCDM hub elements (rows) x source datasets (columns).

Each cell shows how a source maps to that hub element, coloured by SKOS predicate
(exact/close/broad/narrow/related) with alpha scaled by confidence; blank = gap.
Reads hub/eccdm/elements.csv and every mappings/*__to__eccdm.sssom.tsv.

Usage:
    python scripts/heatmap.py [--out docs/coverage-heatmap.png]
"""
from __future__ import annotations

import argparse
import csv
import glob
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
HUB = REPO / "hub" / "eccdm" / "elements.csv"
MAPPINGS = REPO / "mappings"
DEFAULT_OUT = REPO / "docs" / "coverage-heatmap.png"

# predicate -> (colour, short label); rank picks the "strongest" if several rows
PRED = {
    "skos:exactMatch":   ("#1a7d3c", "exact"),
    "skos:closeMatch":   ("#7cb342", "close"),
    "skos:narrowMatch":  ("#4a90d9", "narrow"),
    "skos:broadMatch":   ("#f5a623", "broad"),
    "skos:relatedMatch": ("#b39ddb", "related"),
}
RANK = ["skos:exactMatch", "skos:closeMatch", "skos:narrowMatch",
        "skos:broadMatch", "skos:relatedMatch"]
GAP = "#ececec"


def read_sssom(path: Path) -> list[dict]:
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines()
             if not ln.startswith("#")]
    return list(csv.DictReader(lines, delimiter="\t")) if lines else []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    hub = list(csv.DictReader(HUB.open(encoding="utf-8")))
    row_ids = [r["id"] for r in hub]
    row_lab = [f'{r["model"]}.{r["element"]}' for r in hub]
    # model boundaries for visual grouping
    models = [r["model"] for r in hub]

    files = sorted(glob.glob(str(MAPPINGS / "*__to__eccdm.sssom.tsv")))
    sources = [Path(f).name.split("__to__")[0] for f in files]

    # cell[(obj_id, src)] = (predicate, confidence)
    cell: dict[tuple, tuple] = {}
    for f, src in zip(files, sources):
        for row in read_sssom(Path(f)):
            obj, pred = row.get("object_id"), row.get("predicate_id")
            if not obj or not pred:
                continue
            conf = float(row.get("confidence") or 0.6)
            prev = cell.get((obj, src))
            if prev is None or RANK.index(pred) < RANK.index(prev[0]):
                cell[(obj, src)] = (pred, conf)

    nrows, ncols = len(row_ids), len(sources)
    fig, ax = plt.subplots(figsize=(2.4 + 1.5 * ncols, 0.28 * nrows + 1.5))

    for j in range(ncols):
        for i, obj in enumerate(row_ids):
            hit = cell.get((obj, sources[j]))
            if hit:
                colour, _ = PRED.get(hit[0], ("#999999", "?"))
                rgba = mcolors.to_rgba(colour, alpha=0.35 + 0.65 * hit[1])
            else:
                rgba = mcolors.to_rgba(GAP, alpha=1.0)
            ax.add_patch(plt.Rectangle((j, nrows - 1 - i), 1, 1,
                                       facecolor=rgba, edgecolor="white", lw=0.5))

    # model separators + labels on the right
    ax.set_xlim(0, ncols)
    ax.set_ylim(0, nrows)
    ax.set_xticks([j + 0.5 for j in range(ncols)])
    ax.set_xticklabels(sources, rotation=30, ha="left", fontsize=8)
    ax.xaxis.tick_top()
    ax.set_yticks([nrows - 1 - i + 0.5 for i in range(nrows)])
    ax.set_yticklabels(row_lab, fontsize=6)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # horizontal lines between models
    for i in range(1, nrows):
        if models[i] != models[i - 1]:
            ax.axhline(nrows - i, color="#bbbbbb", lw=0.8)

    covered = len({o for (o, _s) in cell})
    ax.set_title(f"ECCDM hub coverage — {covered}/{nrows} elements mapped by "
                 f">=1 source", fontsize=10, pad=24)

    legend = [Patch(facecolor=c, label=l) for c, l in PRED.values()] + \
             [Patch(facecolor=GAP, label="gap")]
    ax.legend(handles=legend, loc="lower left", bbox_to_anchor=(0, -0.06 - 6/nrows),
              ncol=6, fontsize=7, frameon=False)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches="tight")
    print(f"Wrote {args.out} ({covered}/{nrows} hub elements covered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
