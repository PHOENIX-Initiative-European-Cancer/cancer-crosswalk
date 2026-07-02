#!/usr/bin/env python3
"""Inverse-gap analysis: source-side elements with NO ECCDM hub home.

The hub coverage report (coverage.py) measures how much of ECCDM each source
fills. This does the opposite: it takes every source element that was NOT mapped
to the hub and clusters it into candidate **extension modules** (extension
modules ECCDM would need), classifying each by how it *could* be carried:

  carriage:
    by-reference       -> no hub field, but attachable as referenced evidence
                          IF ECCDM adds an evidence hook + an Observation/Finding
                          logical model (e.g. ER/PR/HER2, BI-RADS, pathology).
    new-module         -> needs a whole new hub model (e.g. tumour board / MDO).
    out-of-scope       -> administrative / genomics-infrastructure, not clinical
                          content ECCDM aims to model.

Reads sources/*/elements.csv + mappings/*__to__eccdm.sssom.tsv.
Writes docs/extension-modules.md and prints a summary.

Usage:
    python scripts/inverse_gaps.py [--out docs/extension-modules.md]
"""
from __future__ import annotations

import argparse
import csv
import glob
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
MAPPINGS = REPO / "mappings"
DEFAULT_OUT = REPO / "docs" / "extension-modules.md"

SOURCES = {
    "mii-onko-obds": "sources/mii-onko-obds/elements.csv",
    "nabon-mammacarcinoom": "sources/nabon-mammacarcinoom/elements.csv",
    "b1mg-cmd": "sources/b1mg-cmd/elements.csv",
    "senologie-datenkranz": "sources/senologie-datenkranz/elements.csv",
}

# candidate extension module -> (carriage, [keywords]). First match wins, so
# order matters: specific clinical clusters before the catch-alls.
MODULES = [
    ("Biomarker / receptor status", "by-reference",
     ["her2", "hormonrez", "oestrogen", "estrogen", "progesteron", "receptor",
      "rezeptor", "ki-67", "ki67", "pd-l1", "pdl1", "immunhisto", "allred", "irs"]),
    ("Imaging findings / BI-RADS", "by-reference",
     ["bi-rads", "birads", "acr", "mammografie", "echografie", "mammograf",
      "massa", "calcificat", "aankleuring", "densiteit", "echogenic", "laesie",
      "beeldvormend", "radiolog", "mri", "echo"]),
    ("Pathology detail", "by-reference",
     ["resekt", "snijvlak", "margin", "sentinel", "schildwacht", "lymfeklier",
      "lymphknoten", "lk_", "invasief", "invasiv", "dcis", "nottingham",
      "mitose", "tubulus", "grading", "breslow", "gleason", "praeparat",
      "specimen", "topografie", "morfolog", "histolog"]),
    ("Molecular tests / genomics", "by-reference",
     ["oncotype", "mammaprint", "genexpress", "genetic", "variant", "mutation",
      "sequenc", "genom", "biomarker", "moleculair"]),
    ("Tumour board / MDO", "new-module",
     ["tumorkonferenz", "tumorboard", "mdo", "konferenz", "advies", "beleid",
      "recommendation", "therapieempfehlung", "besluit"]),
    ("Menopause / patient history", "by-reference",
     ["menopaus", "anamnese", "voorgeschied", "gravida", "para", "familieanamnese",
      "risico", "brca"]),
    ("Surgery detail / reconstruction", "by-reference",
     ["reconstruct", "rekonstru", "drahtmark", "praeparatkontrolle", "stoma",
      "anastomose", "operatie", "resectie", "clavien"]),
    ("Genomics / biobank infrastructure", "out-of-scope",
     ["sample", "sequence", "pipeline", "library", "aliquot", "biobank",
      "specimen_id", "processing"]),
    ("Administrative / submitter", "out-of-scope",
     ["melder", "absender", "submitter", "versicherten", "adresse", "ident",
      "aanvrager", "steward", "consent", "datum van aanmelding", "einsende"]),
]


def load_source(path: Path) -> list[dict]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    for r in rows:
        # unify a searchable text + a display label across the 4 schemas
        r["_text"] = " ".join(str(v) for v in r.values()).lower()
        r["_label"] = r.get("element") or r.get("label") or r.get("id", "")
    return rows


def classify(text: str):
    for module, carriage, kws in MODULES:
        if any(k in text for k in kws):
            return module, carriage
    return "Unclustered / to triage", "review"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    mapped = set()
    for f in glob.glob(str(MAPPINGS / "*__to__eccdm.sssom.tsv")):
        for r in csv.DictReader(
                [l for l in open(f) if not l.startswith("#")], delimiter="\t"):
            if r.get("subject_id"):
                mapped.add(r["subject_id"])

    # module -> carriage, and module -> {source -> [labels]}
    carriage_of = {}
    by_module = defaultdict(lambda: defaultdict(list))
    totals = defaultdict(int)
    for src, path in SOURCES.items():
        for r in load_source(REPO / path):
            if r["id"] in mapped:
                continue
            module, carriage = classify(r["_text"])
            carriage_of[module] = carriage
            by_module[module][src].append(r["_label"])
            totals[src] += 1

    # order modules by carriage then size
    carr_rank = {"by-reference": 0, "new-module": 1, "review": 2, "out-of-scope": 3}
    mods = sorted(by_module, key=lambda m: (carr_rank[carriage_of[m]],
                                            -sum(len(v) for v in by_module[m].values())))

    lines = ["# Extension modules — inverse gaps (source-side, no ECCDM hub home)\n",
             "Generated by `scripts/inverse_gaps.py`. Every source element that maps",
             "to NO ECCDM hub element, clustered into candidate extension modules and",
             "classified by how ECCDM could carry it.\n",
             "- **by-reference** — needs an evidence hook + an Observation/Finding "
             "logical model on the hub; the finding then hangs off by reference.",
             "- **new-module** — needs a whole new hub model.",
             "- **out-of-scope** — administrative / genomics-infrastructure, not "
             "clinical content ECCDM targets.\n",
             f"Unmapped source elements: " +
             ", ".join(f"{s} {totals[s]}" for s in SOURCES) + ".\n"]

    for m in mods:
        n = sum(len(v) for v in by_module[m].values())
        lines.append(f"## {m}  ·  _{carriage_of[m]}_  ({n} fields)\n")
        for src in SOURCES:
            labs = by_module[m].get(src)
            if labs:
                ex = ", ".join(sorted(set(labs))[:8])
                more = f" … (+{len(set(labs)) - 8})" if len(set(labs)) > 8 else ""
                lines.append(f"- **{src}** ({len(labs)}): {ex}{more}")
        lines.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")

    # console summary
    print(f"Wrote {args.out}\n")
    print(f"{'module':38} {'carriage':16} {'fields':>6}")
    for m in mods:
        n = sum(len(v) for v in by_module[m].values())
        print(f"{m:38} {carriage_of[m]:16} {n:6}")
    print(f"\nTotal unmapped source elements: {sum(totals.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
