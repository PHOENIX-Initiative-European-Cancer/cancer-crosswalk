#!/usr/bin/env python3
"""Gap analysis over the SSSOM mapping sets.

For each source dataset (mappings/*__to__eccdm.sssom.tsv), reports how many ECCDM
hub elements are covered, by which predicate, and which hub elements no source
maps to at all (the gaps). The hub is hub/eccdm/elements.csv.

Usage:
    python scripts/coverage.py [--md]   # --md prints a Markdown report
"""
from __future__ import annotations

import argparse
import csv
import glob
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
HUB = REPO / "hub" / "eccdm" / "elements.csv"
MAPPINGS = REPO / "mappings"

EXACT = {"skos:exactMatch", "owl:equivalentClass"}


def read_hub() -> list[dict]:
    with HUB.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def read_sssom(path: Path) -> list[dict]:
    """Read an SSSOM TSV, skipping the leading '#' YAML metadata block."""
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines()
             if not ln.startswith("#")]
    if not lines:
        return []
    reader = csv.DictReader(lines, delimiter="\t")
    return [row for row in reader if row.get("subject_id")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--md", action="store_true", help="emit Markdown")
    args = ap.parse_args()

    hub = read_hub()
    hub_ids = [r["id"] for r in hub]
    label = {r["id"]: f'{r["model"]}.{r["element"]}' for r in hub}

    # object_id -> set of sources that map to it (any predicate)
    covered: dict[str, set[str]] = defaultdict(set)
    exact_covered: dict[str, set[str]] = defaultdict(set)
    per_source_count: dict[str, int] = {}

    for f in sorted(glob.glob(str(MAPPINGS / "*__to__eccdm.sssom.tsv"))):
        src = Path(f).name.split("__to__")[0]
        rows = read_sssom(Path(f))
        per_source_count[src] = len(rows)
        for row in rows:
            obj = row["object_id"]
            covered[obj].add(src)
            if row.get("predicate_id") in EXACT:
                exact_covered[obj].add(src)

    n = len(hub_ids)
    any_cov = sum(1 for i in hub_ids if covered.get(i))
    gaps = [i for i in hub_ids if not covered.get(i)]

    out = []
    p = out.append if args.md else lambda s: print(s)

    p(f"# ECCDM hub coverage\n" if args.md else "=== ECCDM hub coverage ===")
    p(f"Hub elements: {n}")
    p(f"Covered by >=1 source: {any_cov} ({any_cov*100//n}%)")
    p(f"Gaps (no source maps to them): {len(gaps)}\n")

    p("## Mappings per source\n" if args.md else "-- mappings per source --")
    if args.md:
        p("| source | mapping rows |\n|---|---|")
        for s, c in sorted(per_source_count.items()):
            p(f"| {s} | {c} |")
    else:
        for s, c in sorted(per_source_count.items()):
            p(f"  {s}: {c}")

    p("\n## Gaps (uncovered ECCDM hub elements)\n" if args.md
      else "\n-- gaps --")
    for i in gaps:
        p(f"- `{label[i]}`" if args.md else f"  {label[i]}")

    if args.md:
        print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
