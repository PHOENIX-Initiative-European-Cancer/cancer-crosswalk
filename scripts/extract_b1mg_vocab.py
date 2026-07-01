#!/usr/bin/env python3
"""Extract the B1MG 1+MG Minimal Dataset for Cancer spoke vocabulary from the
official Excel workbook.

The dataset lives in a single sheet ('1+MG-MDC'). Every row with a numeric
'Item number' is a data element; rows without an item number are blank filler
rows and are skipped.  Item names are NOT unique across the full dataset (e.g.
'Date', 'ID', 'Anatomy' repeat across multiple sub-domains / sample types),
so the CURIE key is the stable numeric item number: ``b1mg:<n>``.

Columns extracted:
  id          – CURIE  b1mg:<item_number>
  domain      – 'Domain' column (1_SUBMITTER … 8_BIOMARKER)
  element     – 'Item' column (element name)
  datatype    – first-line of 'Value sets' column (normalised type hint)
  terminology – 'Value set reference (Dictionaries or Standards)' column
  definition  – 'Item definition' column

Usage:
    python scripts/extract_b1mg_vocab.py [--xlsx FILE] [--out FILE]
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_XLSX = (
    REPO / "sources" / "b1mg-cmd" / "ref" / "1+MG-MDC_01.xlsx"
)
DEFAULT_OUT = REPO / "sources" / "b1mg-cmd" / "elements.csv"


def _clean(value) -> str:
    """Return stripped string; empty string for None/whitespace."""
    return str(value).strip() if value is not None else ""


def _normalise_datatype(raw: str) -> str:
    """Collapse multi-line enum strings to a terse type hint.

    Multi-line cells carry the full enumeration.  We derive a tidy type label
    from the first non-empty line so the CSV stays readable.
    """
    if not raw:
        return ""
    first = raw.splitlines()[0].strip()
    # Recognise common patterns
    low = first.lower()
    if "date" in low and "iso" in low:
        return "date"
    if "partial date" in low:
        return "date"
    if first.lower() in ("text",):
        return "string"
    if first.lower() in ("integer",):
        return "integer"
    if first.lower() in ("number", "number (gy)"):
        return "decimal"
    if first.lower().startswith("doi"):
        return "uri"
    # Looks like a coded value list (has newlines → enum)
    if "\n" in raw:
        return "code"
    return first


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    wb = openpyxl.load_workbook(args.xlsx, read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    header = [_clean(c) for c in next(rows_iter)]
    idx = {name: i for i, name in enumerate(header)}

    def cell(row, col_name: str) -> str:
        i = idx.get(col_name)
        if i is None or i >= len(row) or row[i] is None:
            return ""
        return str(row[i]).strip()

    out = []
    for row in rows_iter:
        item_num = row[idx.get("Item number", 0)]
        if item_num is None:
            continue  # blank / section header row
        try:
            num = int(item_num)
        except (TypeError, ValueError):
            continue

        domain = cell(row, "Domain")
        element = cell(row, "Item")
        if not element:
            continue

        raw_valset = cell(row, "Value sets")
        datatype = _normalise_datatype(raw_valset)
        terminology = cell(row, "Value set reference (Dictionaries or Standards)")
        definition = cell(row, "Item definition")

        out.append({
            "id": f"b1mg:{num}",
            "domain": domain,
            "element": element,
            "datatype": datatype,
            "terminology": terminology,
            "definition": definition,
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["id", "domain", "element", "datatype", "terminology", "definition"]
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out)

    # per-domain summary
    counts: Counter = Counter(r["domain"] for r in out)
    print(f"Wrote {len(out)} B1MG data elements -> {args.out}")
    print("Per-domain counts:")
    for domain in sorted(counts):
        print(f"  {domain}: {counts[domain]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
