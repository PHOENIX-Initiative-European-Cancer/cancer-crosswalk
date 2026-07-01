#!/usr/bin/env python3
"""Extract the NABON breast-cancer spoke vocabulary from the official Excel.

The NABON 'Informatiestandaard borstkanker' ships as one sheet where real data
elements carry an ID like ``onco-mamma-new-dataelement-729``; the interleaved
rows without such an ID are value-list members and are skipped. One row per data
element -> sources/nabon-mammacarcinoom/elements.csv, keyed ``nabon:<ID-tail>``.

Usage:
    python scripts/extract_nabon_vocab.py [--xlsx FILE] [--out FILE]
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_XLSX = (REPO / "sources" / "nabon-mammacarcinoom" / "ref"
                / "Informatiestandaard-borstkanker-12-nov-2020.xlsx")
DEFAULT_OUT = REPO / "sources" / "nabon-mammacarcinoom" / "elements.csv"
ID_RE = re.compile(r"onco-mamma-new-dataelement-(\d+)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    wb = openpyxl.load_workbook(args.xlsx, read_only=True, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    header = [str(c or "").strip() for c in next(rows)]
    idx = {name: i for i, name in enumerate(header)}

    def cell(row, name):
        i = idx.get(name)
        return (str(row[i]).strip() if i is not None and i < len(row)
                and row[i] is not None else "")

    out = []
    for row in rows:
        rid = cell(row, "ID")
        m = ID_RE.search(rid)
        if not m:
            continue  # value-list member, not an element
        term = cell(row, "Terminologie")
        wl = cell(row, "Waardelijst")
        out.append({
            "id": f"nabon:dataelement-{m.group(1)}",
            "element": cell(row, "Naam"),
            "datatype": cell(row, "Datatype"),
            "terminology": term or (f"Waardelijst: {wl}" if wl else ""),
            "type": cell(row, "Type"),
            "definition": cell(row, "Omschrijving"),
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["id", "element", "datatype", "terminology", "type", "definition"]
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"Wrote {len(out)} NABON data elements -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
