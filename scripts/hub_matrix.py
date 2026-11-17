#!/usr/bin/env python3
"""Hub-side matrix: every ECCDM element x (the mapped standards + INT Milan).

Joins the two kinds of evidence this crosswalk has about each of the 68 hub
elements:

  * from the SSSOM mapping sets — which standard datasets (oBDS, NABON, B1MG,
    Senologie) reach the element, and how closely (best SKOS predicate);
  * from the INT Breast ECCDM workbook — whether the INT Milan data warehouse
    can actually deliver the attribute (present / present via ETL / partial /
    absent / not applicable).

Writes docs/hub-matrix.png (heatmap) and docs/hub-matrix.md (table + summary).

Usage:
    python scripts/hub_matrix.py [--xlsx FILE] [--png FILE] [--md FILE]
"""
from __future__ import annotations

import argparse
import csv
import glob
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import inverse_gaps as ig  # noqa: E402

REPO = ig.REPO
HUB = REPO / "hub" / "eccdm" / "elements.csv"
DEFAULT_XLSX = REPO / "sources" / "int-breast" / "ref" / "INT Breast ECCDM.xlsx"
DEFAULT_PNG = REPO / "docs" / "hub-matrix.png"
DEFAULT_MD = REPO / "docs" / "hub-matrix.md"

SRC_SHORT = {"mii-onko-obds": "oBDS", "nabon-mammacarcinoom": "NABON",
             "b1mg-cmd": "B1MG", "senologie-datenkranz": "Senologie"}
PRED_RANK = {"skos:exactMatch": 4, "skos:closeMatch": 3, "skos:narrowMatch": 2,
             "skos:broadMatch": 2, "skos:relatedMatch": 1}
PRED_SHORT = {4: "exact", 3: "close", 2: "narrow/broad", 1: "related"}
# INT attribute names that differ from the hub element names
INT_ALIAS = {"SexAtDiagnosis": "observedSexGender", "Value": "stage.value"}
NOT_APPLICABLE = {"ActiveSurveillance"}      # not a breast-cancer concept

C_BLUE = {4: "#1c5cab", 3: "#3987e5", 2: "#86b6ef", 1: "#cde2fb", 0: "#f3f2ee"}
C_INT = {"present": "#d55181", "etl": "#e87ba4", "partial": "#f3b7cb", "absent": "#d6d5ce",
         "n/a": "#ffffff", "unknown": "#f3f2ee"}
C_INK, C_INK2, C_MUTED, C_GRID, C_SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#ffffff"


def lower_camel(s: str) -> str:
    return s[0].lower() + s[1:] if s else s


def load_hub():
    rows = list(csv.DictReader(HUB.open(encoding="utf-8")))
    return rows


def load_mappings():
    best = defaultdict(dict)     # object_id -> src -> rank
    for src in ig.SOURCES:
        f = ig.MAPPINGS / f"{src}__to__eccdm.sssom.tsv"
        for r in csv.DictReader([l for l in open(f) if not l.startswith("#")], delimiter="\t"):
            o, p = r.get("object_id"), r.get("predicate_id")
            if not o or p not in PRED_RANK:
                continue
            best[o][src] = max(best[o].get(src, 0), PRED_RANK[p])
    return best


def load_int(xlsx: Path):
    """element id -> (status, format note)."""
    out = {}
    if not xlsx.exists():
        return out
    import openpyxl
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    for ws in wb.worksheets:
        model = ws.title
        if model == "New Variables":
            continue
        for row in ws.iter_rows(min_row=2, values_only=True):
            attr = row[0]
            if not attr or attr == "Attribute":
                continue
            attr = str(attr).strip()
            elem = INT_ALIAS.get(attr) or ".".join(lower_camel(p) for p in attr.split("."))
            eid = f"eccdm:{model}.{elem}"
            pres = str(row[6] or "").strip().lower()
            fmt = str(row[7] or "").strip()
            if model in NOT_APPLICABLE:
                status = "n/a"
            elif pres == "":
                status = None                       # duplicate header block, keep earlier
            elif pres.startswith("yes") and "only" in pres:
                status = "partial"
            elif pres.startswith("yes"):
                status = "etl" if ("etl" in fmt.lower() or "retrievable at the source" in fmt.lower()) else "present"
            elif pres.startswith("no"):
                status = "absent"
            else:
                status = "unknown"
            if status is None and eid in out:
                continue
            note = (pres if pres not in ("yes", "no") else "") + (" · " + fmt.split("\n")[0] if fmt else "")
            out[eid] = (status or "unknown", note.strip(" ·"))
    return out


def is_structural(r: dict) -> bool:
    """Reference links the flat source datasets carry implicitly (never mapped)."""
    return r["element"] == "subject" or r["type"].startswith("Reference") or r["element"] == "stage"


def classify_row(reached: int, int_status: str, structural: bool = False) -> str:
    if int_status == "n/a":
        return "not applicable (breast)"
    if structural:
        return "structural link"
    if int_status == "unknown":
        return "not assessed by INT"
    int_yes = int_status in ("present", "etl", "partial")
    if reached and int_yes:
        return "standards and INT"
    if reached and not int_yes:
        return "standards only"
    if int_yes and not reached:
        return "INT only"
    return "nobody"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--png", type=Path, default=DEFAULT_PNG)
    ap.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = ap.parse_args()

    hub = load_hub()
    best = load_mappings()
    intd = load_int(args.xlsx)
    srcs = list(ig.SOURCES)

    # ---------------- table ----------------
    rows = []
    for r in hub:
        eid = r["id"]
        ranks = {s: best.get(eid, {}).get(s, 0) for s in srcs}
        reached = sum(1 for v in ranks.values() if v)
        st, note = intd.get(eid, ("unknown", ""))
        if r["model"] in NOT_APPLICABLE:
            st = "n/a"
        rows.append({"id": eid, "model": r["model"], "element": r["element"],
                     "ranks": ranks, "reached": reached, "int": st, "note": note,
                     "verdict": classify_row(reached, st, is_structural(r))})
    verdicts = Counter(x["verdict"] for x in rows)

    # markdown
    md = ["# Hub matrix — ECCDM elements × standards × INT Milan\n",
          "Generated by `scripts/hub_matrix.py`. Columns oBDS/NABON/B1MG/Senologie show the",
          "best SKOS predicate of any mapping that reaches the element (`exact` > `close` >",
          "`narrow/broad` > `related`, blank = no mapping). INT = availability of the attribute",
          "in the INT Milan breast data warehouse per the INT Breast ECCDM workbook",
          "(`present`, `etl` = present but derived through ETL, `partial`, `absent`, `n/a` =",
          "model not applicable to breast cancer).\n",
          "## Summary\n",
          "| verdict | elements |", "|---|---|"]
    for k in ("standards and INT", "standards only", "INT only", "nobody", "structural link", "not assessed by INT", "not applicable (breast)"):
        md.append(f"| {k} | {verdicts.get(k, 0)} |")
    md += ["", "## Elements\n",
           "| model | element | " + " | ".join(SRC_SHORT[s] for s in srcs) + " | INT | verdict | INT note |",
           "|---|---|" + "---|" * len(srcs) + "---|---|---|"]
    for x in rows:
        cells = [PRED_SHORT.get(x["ranks"][s], "") for s in srcs]
        md.append(f"| {x['model']} | {x['element']} | " + " | ".join(cells) +
                  f" | {x['int']} | {x['verdict']} | {x['note'][:80]} |")
    args.md.write_text("\n".join(md) + "\n", encoding="utf-8")

    # ---------------- heatmap ----------------
    n = len(rows)
    cols = srcs + ["int"]
    fig, ax = plt.subplots(figsize=(11, 0.235 * n + 3.2), facecolor=C_SURF)
    for i, x in enumerate(rows):
        y = n - 1 - i
        for j, s in enumerate(srcs):
            v = x["ranks"][s]
            ax.add_patch(Rectangle((j, y), 1, 1, facecolor=C_BLUE[v], edgecolor=C_SURF, linewidth=1.5))
            if v:
                ax.text(j + 0.5, y + 0.5, PRED_SHORT[v].replace("narrow/broad", "n/b"),
                        ha="center", va="center", fontsize=6.2,
                        color=C_SURF if v >= 3 else C_INK)
        st = x["int"]
        ax.add_patch(Rectangle((len(srcs) + 0.25, y), 1, 1, facecolor=C_INT[st],
                               edgecolor=C_GRID if st == "n/a" else C_SURF, linewidth=1.2,
                               hatch="////" if st == "n/a" else None))
        if st not in ("n/a", "unknown"):
            ax.text(len(srcs) + 0.75, y + 0.5, {"present": "yes", "etl": "ETL", "partial": "part.",
                                                  "absent": "no"}[st], ha="center", va="center",
                    fontsize=6.2, color=C_SURF if st in ("present", "etl") else C_INK)
        # verdict marker
        vcol = {"standards and INT": "#0ca30c", "standards only": "#2a78d6", "INT only": "#d55181",
                "nobody": "#898781", "structural link": "#e1e0d9", "not assessed by INT": "#e1e0d9",
                "not applicable (breast)": "#c3c2b7"}[x["verdict"]]
        ax.add_patch(Rectangle((len(srcs) + 1.5, y + 0.2), 0.18, 0.6, facecolor=vcol, edgecolor="none"))
        ax.text(len(srcs) + 1.78, y + 0.5, x["verdict"], ha="left", va="center", fontsize=6.2, color=C_INK2)
        ax.text(-0.15, y + 0.5, x["element"], ha="right", va="center", fontsize=6.6, color=C_INK)
    # model separators + labels
    y = n
    for model in dict.fromkeys(x["model"] for x in rows):
        k = sum(1 for x in rows if x["model"] == model)
        ax.plot([-9.4, len(srcs) + 4.3], [y, y], color=C_GRID, linewidth=0.8)
        ax.text(-5.2, y - k / 2, model, ha="right", va="center", fontsize=7, color=C_INK2,
                fontweight="bold")
        y -= k
    ax.plot([-9.4, len(srcs) + 4.3], [0, 0], color=C_GRID, linewidth=0.8)
    for j, s in enumerate(srcs):
        ax.text(j + 0.5, n + 0.3, SRC_SHORT[s], ha="left", va="bottom", fontsize=8, color=C_INK,
                rotation=45)
    ax.text(len(srcs) + 0.75, n + 0.3, "INT Milan (DWH)", ha="left", va="bottom", fontsize=8,
            color=C_INK, rotation=45)
    ax.text(len(srcs) + 1.5, n + 0.3, "standards vs INT", ha="left", va="bottom", fontsize=8,
            color=C_INK, rotation=45)
    ax.set_xlim(-9.6, len(srcs) + 4.3); ax.set_ylim(-0.3, n + 3.4)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("cancer-crosswalk — the 68 ECCDM elements\nreached by the mapped standards "
                 "(blue, by predicate strength) vs available at INT Milan (pink)", fontsize=9.5,
                 loc="left", color=C_INK, pad=10)
    handles = [Patch(facecolor=C_BLUE[4], label="exact"), Patch(facecolor=C_BLUE[3], label="close"),
               Patch(facecolor=C_BLUE[2], label="narrow / broad"), Patch(facecolor=C_BLUE[1], label="related"),
               Patch(facecolor=C_INT["present"], label="INT present"), Patch(facecolor=C_INT["etl"], label="INT via ETL"),
               Patch(facecolor=C_INT["partial"], label="INT partial"), Patch(facecolor=C_INT["absent"], label="INT absent")]
    sums = "  ·  ".join(f"{k}: {verdicts.get(k, 0)}" for k in ("standards and INT", "standards only", "INT only", "nobody", "structural link", "not assessed by INT", "not applicable (breast)"))
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, fontsize=7.5,
               bbox_to_anchor=(0.5, 0.012))
    fig.text(0.5, 0.055, sums, ha="center", fontsize=7.5, color=C_INK2)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.085)
    fig.savefig(args.png, dpi=150, facecolor=C_SURF)
    print(f"Wrote {args.png} and {args.md}")
    for k in ("standards and INT", "standards only", "INT only", "nobody", "structural link", "not assessed by INT", "not applicable (breast)"):
        print(f"  {k:26s} {verdicts.get(k, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
