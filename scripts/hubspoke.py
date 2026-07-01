#!/usr/bin/env python3
"""Hub-and-spoke diagram: ECCDM at the centre, source datasets as spokes.

Two panels:
  (left)  radial hub-spoke — ECCDM centre, one spoke per source; edge width =
          number of mappings, edge colour = dominant SKOS predicate, spoke badge
          = models touched / 11 and hub-element coverage.
  (right) per-source predicate mix (stacked bar) — how each source relates to the
          hub (exact/close/narrow/broad/related).

Reads mappings/*__to__eccdm.sssom.tsv and hub/eccdm/elements.csv.

Usage:
    python scripts/hubspoke.py [--out docs/hub-spoke.png]
"""
from __future__ import annotations

import argparse
import csv
import glob
import math
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
HUB = REPO / "hub" / "eccdm" / "elements.csv"
MAPPINGS = REPO / "mappings"
DEFAULT_OUT = REPO / "docs" / "hub-spoke.png"

PRED = {
    "skos:exactMatch":   ("#1a7d3c", "exact"),
    "skos:closeMatch":   ("#7cb342", "close"),
    "skos:narrowMatch":  ("#4a90d9", "narrow"),
    "skos:broadMatch":   ("#f5a623", "broad"),
    "skos:relatedMatch": ("#b39ddb", "related"),
}
ORDER = list(PRED.keys())
LABELS = {"b1mg-cmd": "B1MG\n(EU minimal)",
          "mii-onko-obds": "oBDS\n(DE registry)",
          "nabon-mammacarcinoom": "NABON\n(NL breast)",
          "senologie-datenkranz": "Senologie\n(DE breast)"}


def read_sssom(path: Path) -> list[dict]:
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines()
             if not ln.startswith("#")]
    return list(csv.DictReader(lines, delimiter="\t")) if lines else []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    hub = list(csv.DictReader(HUB.open(encoding="utf-8")))
    n_hub = len(hub)
    n_models = len({r["model"] for r in hub})

    stats = {}
    for f in sorted(glob.glob(str(MAPPINGS / "*__to__eccdm.sssom.tsv"))):
        src = Path(f).name.split("__to__")[0]
        rows = read_sssom(Path(f))
        preds = Counter(r["predicate_id"] for r in rows if r.get("predicate_id"))
        objs = {r["object_id"] for r in rows if r.get("object_id")}
        models = {o.split(".")[0] for o in objs}
        stats[src] = {"n": len(rows), "preds": preds,
                      "elements": len(objs), "models": len(models)}

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 7),
                                   gridspec_kw={"width_ratios": [1.15, 1]})

    # ---- left: radial hub-spoke ----
    axL.set_xlim(-1.5, 1.5)
    axL.set_ylim(-1.5, 1.5)
    axL.set_aspect("equal")
    axL.axis("off")
    srcs = list(stats.keys())
    maxn = max(s["n"] for s in stats.values())
    angles = [math.pi / 2 + i * 2 * math.pi / len(srcs) for i in range(len(srcs))]
    for ang, src in zip(angles, srcs):
        x, y = 1.05 * math.cos(ang), 1.05 * math.sin(ang)
        st = stats[src]
        dom = st["preds"].most_common(1)[0][0] if st["preds"] else "skos:closeMatch"
        colour = PRED.get(dom, ("#999", ""))[0]
        lw = 1.5 + 9 * st["n"] / maxn
        axL.plot([0, x], [0, y], color=colour, lw=lw, alpha=0.75,
                 solid_capstyle="round", zorder=1)
        axL.scatter([x], [y], s=2600, color="white", edgecolor=colour,
                    linewidth=2.2, zorder=2)
        axL.text(x, y + 0.02, LABELS.get(src, src), ha="center", va="center",
                 fontsize=8.5, fontweight="bold", zorder=3)
        axL.text(x, y - 0.16, f'{st["n"]} maps · {st["models"]}/{n_models} models',
                 ha="center", va="center", fontsize=7, color="#555", zorder=3)
        # edge weight label at midpoint
        axL.text(0.5 * x, 0.5 * y, str(st["n"]), ha="center", va="center",
                 fontsize=8, color=colour, fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"), zorder=3)
    axL.scatter([0], [0], s=6800, color="#2c3e50", zorder=4)
    covered = len({o for s in stats for o in
                   {r["object_id"] for r in read_sssom(MAPPINGS / f"{s}__to__eccdm.sssom.tsv") if r.get("object_id")}})
    axL.text(0, 0.06, "ECCDM", ha="center", va="center", color="white",
             fontsize=12, fontweight="bold", zorder=5)
    axL.text(0, -0.10, f"{covered}/{n_hub}\nelements", ha="center", va="center",
             color="#d5dbe0", fontsize=7.5, zorder=5)
    axL.set_title("Hub & spoke — each source mapped TO the ECCDM hub\n"
                  "(edge width = #mappings, colour = dominant predicate)",
                  fontsize=10)

    # ---- right: predicate mix per source ----
    ypos = range(len(srcs))
    for i, src in enumerate(srcs):
        left = 0
        for p in ORDER:
            v = stats[src]["preds"].get(p, 0)
            if v:
                axR.barh(i, v, left=left, color=PRED[p][0],
                         edgecolor="white", height=0.62)
                if v >= 2:
                    axR.text(left + v / 2, i, str(v), ha="center", va="center",
                             fontsize=7, color="white", fontweight="bold")
                left += v
    axR.set_yticks(list(ypos))
    axR.set_yticklabels([LABELS.get(s, s).replace("\n", " ") for s in srcs], fontsize=8)
    axR.set_xlabel("number of mappings")
    axR.set_title("How each source relates to the hub\n(predicate mix)", fontsize=10)
    for sp in ("top", "right"):
        axR.spines[sp].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c, _ in PRED.values()]
    axR.legend(handles, [l for _, l in PRED.values()], ncol=5, fontsize=7.5,
               loc="lower center", bbox_to_anchor=(0.5, -0.22), frameon=False)

    fig.suptitle("cancer-crosswalk — ECCDM hub-and-spoke coverage",
                 fontsize=13, fontweight="bold")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches="tight")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
