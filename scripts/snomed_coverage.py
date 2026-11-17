#!/usr/bin/env python3
"""SNOMED CT coverage, per domain, for the two sources where the code layer is known.

Panel A  INT Milan: local codes mapped to SNOMED CT (mappings/int-breast__values__to__snomed),
         per ECCDM model, by match strength (exact / close / broad or narrow / no SNOMED concept).
Panel B  Senologie-Datenkranz: the SenologieOnFHIR value sets, per clinical domain, by the code
         system they draw from (SNOMED CT only / SNOMED CT plus a local code system / another
         standard terminology / local code system only).

The Senologie value-set scan is cached in sources/senologie-datenkranz/valuesets.csv; refresh it
with --scan-senologie when the IG checkout (../SenologieOnFHIR) changes.

Usage:
    python scripts/snomed_coverage.py [--slide] [--scan-senologie] [--out docs/snomed-coverage.png]
"""
from __future__ import annotations

import argparse
import csv
import glob
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

import figstyle as fs

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
INT_MAP = REPO / "mappings" / "int-breast__values__to__snomed.sssom.tsv"
INT_VALUES = REPO / "sources" / "int-breast" / "values.csv"
SENO_VS = REPO / "sources" / "senologie-datenkranz" / "valuesets.csv"
SENO_IG = REPO.parent / "SenologieOnFHIR" / "input" / "fsh"
DEFAULT_OUT = REPO / "docs" / "snomed-coverage.png"
FS = 1.0

MODEL_ORDER = ["CancerPatient", "CancerConditionAtDiagnosis", "CancerStage", "Imaging",
               "Surgery", "Radiotherapy", "SystemicTreatment", "LastFollowUp"]
MODEL_LABEL = {"CancerPatient": "Patient", "CancerConditionAtDiagnosis": "Condition at diagnosis",
               "CancerStage": "Stage", "Imaging": "Imaging", "Surgery": "Surgery",
               "Radiotherapy": "Radiotherapy", "SystemicTreatment": "Systemic treatment",
               "LastFollowUp": "Last follow-up"}
MATCH = [("exact", "exact match", fs.HUB_RAMP[4]), ("close", "close match", fs.HUB_RAMP[3]),
         ("broad/narrow", "broader or narrower concept", fs.HUB_RAMP[2]),
         ("none", "no SNOMED CT concept", fs.CORAL)]
PRED = {"skos:exactMatch": "exact", "skos:closeMatch": "close",
        "skos:narrowMatch": "broad/narrow", "skos:broadMatch": "broad/narrow"}

# Senologie value sets -> clinical domain, by name token (first match wins)
DOMAIN_RULES = [
    ("Patient & history", ["Menopausen", "Raucher", "Verwandtschaft", "Familien", "Kontrazeption", "ECOG", "JaNein"]),
    ("Imaging", ["Bildgebung", "BIRADS", "ACR_", "Mikrokalk", "LK_Status", "US_DEGUM", "Beurteilbarkeit", "Standort", "Auffaellig"]),
    ("Pathology & biomarkers", ["Praeparat", "Histologie", "Grading", "HER2", "ISH_", "IHC_", "Genexpression", "R_Status", "Risikoklasse", "B_Klassifikation", "B3"]),
    ("Follow-up & outcome", ["Nachsorge", "Kontrolltermin", "Verlauf", "RECIST", "Tumornachweis", "Zweittumor", "FollowUp"]),
    ("Therapy", ["Operation", "PreOp", "RT_", "Systemtherapie", "Therapie_", "Applikationsart", "Dosis", "Begleit", "Clavien", "Komplikation", "Ptosis", "Symmetrie", "Lymphoedem"]),
    ("Registry & organisation", ["Tumorboard", "Primaerfallart"]),
    ("Diagnosis & staging", ["Diagnose", "TNM", "UICC", "L_Kategorie", "V_Kategorie", "Pn_Kategorie", "Seite", "Quadrant", "Tumormanifestation",
                             "Metastasierung", "Fernmetastasen", "ICD10", "Detektion", "Screening", "Vorstellungsgrund", "ClockFace"]),
]
DOMAIN_ORDER = ["Patient & history", "Diagnosis & staging", "Imaging", "Pathology & biomarkers",
                "Therapy", "Follow-up & outcome", "Registry & organisation"]
VSCLASS = [("sct", "SNOMED CT only", fs.HUB_RAMP[4]), ("sct+local", "SNOMED CT plus local codes", fs.HUB_RAMP[3]),
           ("other-std", "other standard: UICC, LOINC, ICD, HL7", fs.HUB_RAMP[2]), ("local", "local codes only", fs.CORAL)]


# ------------------------------------------------------------------ INT ---
def int_coverage():
    rows = [r for r in csv.DictReader([l for l in INT_MAP.open(encoding="utf-8") if not l.startswith("#")],
                                      delimiter="\t")]
    model_of = {r["id"]: r["model"] for r in csv.DictReader(INT_VALUES.open(encoding="utf-8"))}
    rank = {"exact": 0, "close": 1, "broad/narrow": 2, "none": 3}
    best = {}
    for r in rows:
        cls = "none" if r["object_id"].startswith("sssom:") else PRED[r["predicate_id"]]
        if rank[cls] < rank.get(best.get(r["subject_id"], "none"), 9) or r["subject_id"] not in best:
            best[r["subject_id"]] = cls
    per = defaultdict(Counter)
    for sid, cls in best.items():
        model = model_of.get(sid) or sid.split(":")[1].split(".")[0]
        per[model][cls] += 1
    return per


# ------------------------------------------------------------ Senologie ---
def scan_senologie() -> list[dict]:
    files = glob.glob(str(SENO_IG / "**" / "*.fsh"), recursive=True)
    alias = {}
    for f in files:
        for m in re.finditer(r"^Alias:\s*(\$?\S+)\s*=\s*(\S+)", Path(f).read_text(encoding="utf-8"), re.M):
            alias[m.group(1)] = m.group(2)

    def sysname(tok):
        tok = alias.get(tok, tok); t = tok.lower()
        for key, name in (("snomed", "SNOMED"), ("loinc", "LOINC"), ("icd", "ICD"), ("medizininformatik", "MII"),
                          ("hl7.org", "HL7"), ("terminology.hl7", "HL7"), ("ucum", "UCUM"), ("unitsofmeasure", "UCUM"),
                          ("uicc", "UICC")):
            if key in t:
                return name
        return "local:" + tok.split("/")[-1]

    out = []
    for f in files:
        txt = Path(f).read_text(encoding="utf-8")
        for pt in re.split(r"^(?=(?:ValueSet|CodeSystem|Profile|Extension|Logical|Instance|Mapping|Invariant|RuleSet):)",
                           txt, flags=re.M):
            m = re.match(r"^ValueSet:\s*(\S+)", pt)
            if not m:
                continue
            title = re.search(r'^Title:\s*"([^"]*)"', pt, re.M)
            systems = set()
            for mm in re.finditer(r"codes from (?:system|valueset) (\S+)", pt):
                systems.add(sysname(mm.group(1)))
            for mm in re.finditer(r"^\*\s+(?:include\s+)?(\$?[A-Za-z0-9_\-\.:/]+)#", pt, re.M):
                systems.add(sysname(mm.group(1)))
            out.append({"name": m.group(1), "title": title.group(1) if title else "",
                        "systems": "|".join(sorted(systems))})
    return sorted(out, key=lambda r: r["name"])


def vs_class(systems: str) -> str:
    s = set(filter(None, systems.split("|")))
    local = {x for x in s if x.startswith("local:")}
    std = s - local
    if "SNOMED" in s and not local:
        return "sct"
    if "SNOMED" in s:
        return "sct+local"
    if std - {"UCUM"}:
        return "other-std"
    return "local"


def vs_domain(name: str) -> str:
    for dom, keys in DOMAIN_RULES:
        if any(k in name for k in keys):
            return dom
    return "Diagnosis & staging"


def seno_coverage():
    per = defaultdict(Counter)
    for r in csv.DictReader(SENO_VS.open(encoding="utf-8")):
        per[vs_domain(r["name"])][vs_class(r["systems"])] += 1
    return per


# ---------------------------------------------------------------- figure ---
def stacked(ax, per, order, labels, classes, title, unit, n_cov):
    ys = [m for m in order if m in per]
    tot = {m: sum(per[m].values()) for m in ys}
    for i, m in enumerate(ys):
        left = 0
        for key, _, col in classes:
            v = per[m][key]
            if not v:
                continue
            ax.barh(i, v, left=left, height=0.62, color=col, edgecolor=fs.SURF, linewidth=1.5)
            if v >= max(3, 0.08 * max(tot.values())):
                ax.text(left + v / 2, i, str(v), ha="center", va="center", fontsize=8 * FS,
                        color=fs.SURF if col != fs.HUB_RAMP[2] else fs.INK)
            left += v
        sct = sum(per[m][k] for k, _, _ in classes[:n_cov])
        ax.text(left + 0.8, i, f"{100 * sct / tot[m]:.0f} %", va="center", fontsize=8.5 * FS,
                color=fs.INK, fontweight="bold")
    ax.set_yticks(range(len(ys)))
    ax.set_yticklabels([f"{labels.get(m, m)}  (n = {tot[m]})" for m in ys], fontsize=9 * FS)
    ax.invert_yaxis()
    ax.set_xlim(0, max(tot.values()) * 1.2)
    ax.set_xlabel(unit, fontsize=8.5 * FS)
    ax.tick_params(length=0, labelsize=8 * FS)
    ax.xaxis.grid(True, color=fs.GRID, linewidth=0.8); ax.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(fs.GRID)
    ax.set_title(title, fontsize=10 * FS, loc="left", pad=10 * FS, color=fs.INK)
    ax.legend(handles=[Patch(facecolor=c, label=l) for _, l, c in classes], loc="upper left",
              bbox_to_anchor=(0, -0.16 if FS == 1 else -0.2), ncol=2, frameon=False,
              fontsize=7.5 * FS, handlelength=1.2, columnspacing=1.4)
    all_sct = sum(per[m][k] for m in ys for k, _, _ in classes[:n_cov]); all_n = sum(tot.values())
    return all_sct, all_n


def main() -> int:
    global FS
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--slide", action="store_true", help="slide version: larger type, no figure title")
    ap.add_argument("--scan-senologie", action="store_true", help="refresh valuesets.csv from the IG checkout")
    args = ap.parse_args()
    FS = 1.35 if args.slide else 1.0
    fs.apply()
    if args.slide and args.out == DEFAULT_OUT:
        args.out = DEFAULT_OUT.with_name("snomed-coverage-slide.png")
    if args.scan_senologie or not SENO_VS.exists():
        rows = scan_senologie()
        with SENO_VS.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["name", "title", "systems"]); w.writeheader(); w.writerows(rows)
        print(f"Wrote {SENO_VS} ({len(rows)} value sets)")

    int_per = int_coverage()
    seno_per = seno_coverage()
    fig = plt.figure(figsize=(16, 7.6) if args.slide else (13, 6.5))
    gs = fig.add_gridspec(1, 2, wspace=0.7, left=0.15, right=0.97, top=0.87, bottom=0.21)
    axA = fig.add_subplot(gs[0]); axB = fig.add_subplot(gs[1])
    a_sct, a_n = stacked(axA, int_per, MODEL_ORDER, MODEL_LABEL, MATCH,
                         "A · INT Milan: local codes with a SNOMED CT concept\n"
                         "per ECCDM model, code level; % = codes with a concept", "local codes", 3)
    b_sct, b_n = stacked(axB, seno_per, DOMAIN_ORDER, {}, VSCLASS,
                         "B · Senologie: value sets drawing on SNOMED CT\n"
                         "per domain, value-set level; % = sets with SNOMED CT content", "value sets", 2)
    print(f"INT: {a_sct}/{a_n} local codes with a SNOMED concept ({100 * a_sct / a_n:.0f} %); "
          f"Senologie: {b_sct}/{b_n} value sets with SNOMED content ({100 * b_sct / b_n:.0f} %)")
    if not args.slide:
        fig.suptitle("cancer-crosswalk — SNOMED CT coverage where the code layer is known",
                     fontsize=13, fontweight="bold", y=0.985)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150, bbox_inches=None if args.slide else "tight")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
