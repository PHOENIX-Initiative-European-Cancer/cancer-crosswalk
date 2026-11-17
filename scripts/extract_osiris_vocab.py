#!/usr/bin/env python3
"""Extract the OSIRIS vocabulary from its ISO 11179-style data dictionary.

Reads ``sources/osiris/ref/DataElementConcept.tsv`` (siric-osiris/OSIRIS,
``data/DataElementConcept.tsv``) and emits one row per data element concept to
``sources/osiris/elements.csv``.

Element id = ``osiris:<DataElementConcept>`` (e.g. ``osiris:Patient_Gender``),
which is the identifier OSIRIS itself uses in its pivot files. The ISO
``IdDataElementConcept`` (C1, C2, ...) is kept as a column.

Usage:
    python scripts/extract_osiris_vocab.py [--tsv FILE] [--out FILE]
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_TSV = REPO / "sources" / "osiris" / "ref" / "DataElementConcept.tsv"
DEFAULT_OUT = REPO / "sources" / "osiris" / "elements.csv"

# ObjectClass -> coarse domain, so the classifier gets a parent context
DOMAIN = {
    "Patient": "patient", "Consent": "patient", "FamilyCancerHistory": "patient",
    "RelatedPathology": "patient",
    "TumorPathologyEvent": "tumour", "TNM": "tumour",
    "Treatment": "treatment", "Drug": "treatment", "AdverseEvent": "treatment",
    "ResponseEvaluation": "treatment",
    "BiologicalSample": "sample",
    "Analysis": "omics", "Technology": "omics", "Panel": "omics",
    "AnalysisProcess": "omics", "OmicAnalysis": "omics", "Alteration": "omics",
    "AlterationOnSample": "omics", "Variant": "omics", "VariantInSample": "omics",
    "CNV": "omics", "Fusion": "omics", "GeneExpression": "omics",
    "GenomeEntity": "omics", "Annotation": "omics", "Validation": "omics",
    "Biomarker": "omics",
    "Study": "imaging", "Series": "imaging", "CommonImage": "imaging",
    "CTImage": "imaging", "MRImage": "imaging", "PTImage": "imaging",
    "NMImage": "imaging", "DXImage": "imaging", "Injection": "imaging",
    "Equipment": "imaging", "ROISegmentation": "imaging",
    "RadiomicsCriteria": "imaging", "RadiomicsFeature": "imaging",
    "RadiomicsImageFilter": "imaging",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tsv", type=Path, default=DEFAULT_TSV)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = list(csv.DictReader(args.tsv.open(encoding="utf-8"), delimiter="\t"))
    out = []
    last_class = ""
    for r in rows:
        dec = r["DataElementConcept"].strip()
        if not dec:
            continue
        oc = r["ObjectClass"].strip() or dec.split("_")[0]
        last_class = oc
        out.append({
            "id": f"osiris:{dec}",
            "iso_id": r["IdDataElementConcept"].strip(),
            "module": oc,
            "domain": DOMAIN.get(oc, "other"),
            "element": dec,
            "label": r["ObjectPropertyLabelEN"].strip(),
            "required": r["Required"].strip(),
            "datatype": r["FormatConceptualDomain"].strip(),
            "terminology": r["ConceptualDomain"].strip(),
            "definition": r["DataElementConceptDefEN"].strip(),
        })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    print(f"Wrote {args.out}: {len(out)} elements")
    from collections import Counter
    for d, n in Counter(o["domain"] for o in out).most_common():
        print(f"  {d}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
