#!/usr/bin/env python3
"""Extract the ECCDM hub vocabulary from the cancer-common FSH LogicalModels.

Parses ``Logical:`` definitions in ``cancer-common/input/fsh/models/*.fsh`` and
emits one row per data element to ``hub/eccdm/elements.csv``. These rows are the
*hub* (the nave) against which every source dataset is mapped via SSSOM.

Element id = ``eccdm:<Model>.<path>`` (a CURIE; see ``prefixes.yaml``).

Usage:
    python scripts/extract_eccdm_hub.py [--models DIR] [--out FILE]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_MODELS = REPO.parent / "cancer-common" / "input" / "fsh" / "models"
DEFAULT_OUT = REPO / "hub" / "eccdm" / "elements.csv"

LOGICAL_RE = re.compile(r"^Logical:\s*(\S+)")
TITLE_RE = re.compile(r'^Title:\s*"([^"]*)"')
# * <path> <card> <type> "<label>"   (type may be Reference(...) or a datatype)
ELEM_RE = re.compile(
    r'^\*\s+([A-Za-z][\w.]*)\s+(\d+\.\.[\d*]+)\s+(.+?)\s+"([^"]*)"\s*$'
)
DEF_RE = re.compile(r'^\*\s+([A-Za-z][\w.]*)\s+\^definition\s*=\s*"(.*)"\s*$')


def parse_file(path: Path) -> list[dict]:
    model = None
    title = None
    rows: dict[str, dict] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if m := LOGICAL_RE.match(line):
            model = m.group(1)
            continue
        if m := TITLE_RE.match(line):
            title = m.group(1)
            continue
        if m := ELEM_RE.match(line):
            path_, card, type_, label = m.groups()
            rows[path_] = {
                "id": f"eccdm:{model}.{path_}",
                "model": model,
                "model_title": title or model,
                "element": path_,
                "label": label,
                "cardinality": card,
                "type": type_.strip(),
                "definition": "",
            }
            continue
        if m := DEF_RE.match(line):
            path_, definition = m.groups()
            if path_ in rows:
                rows[path_]["definition"] = definition.replace("\\n", " ").strip()
    return list(rows.values())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", type=Path, default=DEFAULT_MODELS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.models.is_dir():
        print(f"ERROR: models dir not found: {args.models}", file=sys.stderr)
        return 1

    all_rows: list[dict] = []
    for fsh in sorted(args.models.glob("*.fsh")):
        all_rows.extend(parse_file(fsh))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["id", "model", "model_title", "element", "label",
              "cardinality", "type", "definition"]
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)

    models = sorted({r["model"] for r in all_rows})
    print(f"Wrote {len(all_rows)} hub elements from {len(models)} models -> {args.out}")
    for mdl in models:
        n = sum(1 for r in all_rows if r["model"] == mdl)
        print(f"  {mdl}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
