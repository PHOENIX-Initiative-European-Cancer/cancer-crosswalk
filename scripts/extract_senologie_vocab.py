#!/usr/bin/env python3
"""Extract the Senologie-Datenkranz vocabulary from the BIH Senologie FSH LogicalModel.

Parses the single ``Logical: BIH_LM_Senologie`` definition in
``bih-lm-senologie-complete.fsh`` and emits one row per data element to
``sources/senologie-datenkranz/elements.csv``.

The FSH uses indented ``*`` lines to express nesting (BackboneElement children).
Indent depth (2 spaces per level) is used to reconstruct full dotted paths.
Stops at the first ``Mapping:`` block so downstream oBDS/IQTIG/OncoBox mapping
annotations are not mistaken for element definitions.

Element id = ``senol:BIH_LM_Senologie.<full.dotted.path>`` (CURIE).

Usage:
    python scripts/extract_senologie_vocab.py [--fsh FILE] [--out FILE]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_FSH = (
    REPO.parent
    / "SenologieOnFHIR"
    / "input"
    / "fsh"
    / "bih-lm-senologie-complete.fsh"
)
DEFAULT_OUT = REPO / "sources" / "senologie-datenkranz" / "elements.csv"

LOGICAL_RE = re.compile(r"^Logical:\s*(\S+)")
TITLE_RE = re.compile(r'^Title:\s*"([^"]*)"')
MAPPING_RE = re.compile(r"^Mapping:\s*\S+")

# Matches indented element lines with one or two quoted strings:
#   (indent)(name)(card)(type)"label" ["definition"]
# type may contain spaces (BackboneElement, CodeableConcept, Reference(...), etc.)
ELEM_RE = re.compile(
    r'^(\s*)\*\s+([A-Za-z]\w*)\s+(\d+\.\.[\d*]+)\s+(.+?)\s+"([^"]*)"'
    r'(?:\s+"([^"]*)")?\s*$'
)
# Handles optional ^definition = "..." overrides (uncommon in this file)
DEF_RE = re.compile(
    r'^(\s*)\*\s+([A-Za-z][\w.]*)\s+\^definition\s*=\s*"(.*)"\s*$'
)


def parse_file(path: Path) -> list[dict]:
    model: str | None = None
    in_logical = False
    rows: dict[str, dict] = {}  # keyed by full dotted path

    # Stack of (raw_indent_spaces, name) for path reconstruction.
    # We use raw space count (not divided) so no assumption about indent step.
    path_stack: list[tuple[int, str]] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()

        if m := LOGICAL_RE.match(line):
            model = m.group(1)
            in_logical = True
            path_stack.clear()
            continue

        if not in_logical:
            continue

        # Stop at first Mapping: block (oBDS, IQTIG, OncoBox, etc.)
        if MAPPING_RE.match(line):
            break

        if TITLE_RE.match(line):
            # Title is stored in the model variable already; skip here
            continue

        # Skip metadata annotations (^status, ^description, ^extension, etc.)
        if re.match(r"^\s*\*\s+\^", line):
            continue

        if m := ELEM_RE.match(line):
            indent_str = m.group(1)
            name = m.group(2)
            card = m.group(3)
            type_ = m.group(4).strip()
            label = m.group(5)
            definition = (m.group(6) or "").replace("\\n", " ").strip()

            raw_indent = len(indent_str)

            # Pop stack entries at the same or deeper indent level,
            # then push the current entry.
            while path_stack and path_stack[-1][0] >= raw_indent:
                path_stack.pop()
            path_stack.append((raw_indent, name))

            full_path = ".".join(n for _, n in path_stack)
            rows[full_path] = {
                "id": f"senol:{model}.{full_path}",
                "model": model,
                "element": full_path,
                "label": label,
                "cardinality": card,
                "type": type_,
                "definition": definition,
            }
            continue

        if m := DEF_RE.match(line):
            _, rel_path, definition = m.groups()
            if rel_path in rows:
                rows[rel_path]["definition"] = (
                    definition.replace("\\n", " ").strip()
                )

    return list(rows.values())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--fsh",
        type=Path,
        default=DEFAULT_FSH,
        metavar="FILE",
        help="FSH file containing BIH_LM_Senologie (default: %(default)s)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        metavar="FILE",
        help="Output CSV path (default: %(default)s)",
    )
    args = ap.parse_args()

    if not args.fsh.is_file():
        print(f"ERROR: FSH file not found: {args.fsh}", file=sys.stderr)
        return 1

    all_rows = parse_file(args.fsh)

    if not all_rows:
        print("ERROR: no elements extracted – check the FSH path/format",
              file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["id", "model", "element", "label", "cardinality", "type", "definition"]
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)

    print(f"Wrote {len(all_rows)} Senologie elements -> {args.out}")
    print()
    print("Sample (first 15 rows):")
    for r in all_rows[:15]:
        print(f"  {r['id'][:65]:<65s}  {r['type']:<20s}  {r['label']}")

    # Summary by top-level section
    print()
    print("Elements per top-level section:")
    sections: dict[str, int] = {}
    for r in all_rows:
        top = r["element"].split(".")[0]
        sections[top] = sections.get(top, 0) + 1
    for sec, cnt in sorted(sections.items(), key=lambda x: -x[1]):
        print(f"  {sec}: {cnt}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
