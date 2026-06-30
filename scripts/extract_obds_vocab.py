#!/usr/bin/env python3
"""Extract the oBDS spoke vocabulary from the official oBDS XSD.

Walks every xs:element in the schema and emits one row per element, keyed by its
enclosing complexType (the oBDS module). The element id is a CURIE of the form
``obds:<ComplexType>.<element>`` so each mapping row is traceable to the XSD.

Usage:
    python scripts/extract_obds_vocab.py [--xsd FILE] [--out FILE]
"""
from __future__ import annotations

import argparse
import csv
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_XSD = REPO / "sources" / "mii-onko-obds" / "ref" / "oBDS_v3.0.5.xsd"
DEFAULT_OUT = REPO / "sources" / "mii-onko-obds" / "elements.csv"
XS = "{http://www.w3.org/2001/XMLSchema}"


def local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def doc_of(node: ET.Element) -> str:
    ann = node.find(f"{XS}annotation/{XS}documentation")
    if ann is not None and ann.text:
        return " ".join(ann.text.split())
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xsd", type=Path, default=DEFAULT_XSD)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tree = ET.parse(args.xsd)
    root = tree.getroot()
    parent = {c: p for p in root.iter() for c in p}

    def enclosing_type(node: ET.Element) -> str:
        cur = parent.get(node)
        while cur is not None:
            if local(cur.tag) == "complexType" and cur.get("name"):
                return cur.get("name").removesuffix("_Typ")
            cur = parent.get(cur)
        return "(root)"

    rows = []
    for el in root.iter(f"{XS}element"):
        name = el.get("name")
        if not name:
            continue
        rows.append({
            "id": f"obds:{enclosing_type(el)}.{name}",
            "module": enclosing_type(el),
            "element": name,
            "type": (el.get("type") or "(inline)").removeprefix("tns:"),
            "min": el.get("minOccurs", "1"),
            "max": el.get("maxOccurs", "1"),
            "definition": doc_of(el),
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["id", "module", "element", "type", "min", "max", "definition"]
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    mods = sorted({r["module"] for r in rows})
    print(f"Wrote {len(rows)} oBDS elements from {len(mods)} modules -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
