#!/usr/bin/env python3
"""Verify every SNOMED CT object in an SSSOM mapping set against a Snowstorm.

For each row whose ``object_id`` is a ``sct:`` CURIE, fetch the concept from
the Snowstorm branch and check that it exists, is active, and that its FSN
equals ``object_label``. Rows with ``sssom:NoTermFound`` are skipped. Exit
code 1 if any check fails.

Usage:
    python scripts/verify_snomed_mapping.py mappings/int-breast__values__to__snomed.sssom.tsv \
        [--snowstorm http://localhost:8090] [--branch MAIN/2026-10-01]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tsv", type=Path)
    ap.add_argument("--snowstorm", default="http://localhost:8090")
    ap.add_argument("--branch", default="MAIN/2026-10-01")
    args = ap.parse_args()

    lines = [l for l in args.tsv.read_text(encoding="utf-8").splitlines() if not l.startswith("#")]
    rows = list(csv.DictReader(lines, delimiter="\t"))
    cache: dict[str, dict | None] = {}
    bad = 0
    checked = 0
    for r in rows:
        oid = r["object_id"]
        if not oid.startswith("sct:"):
            continue
        sctid = oid.split(":", 1)[1]
        checked += 1
        if sctid not in cache:
            url = f"{args.snowstorm}/{args.branch}/concepts/{sctid}"
            try:
                cache[sctid] = json.load(urllib.request.urlopen(url, timeout=30))
            except Exception:
                cache[sctid] = None
        c = cache[sctid]
        if c is None:
            print(f"MISSING  {r['subject_id']} -> {oid}"); bad += 1; continue
        if not c.get("active"):
            print(f"INACTIVE {r['subject_id']} -> {oid} {c['fsn']['term']}"); bad += 1; continue
        fsn = c["fsn"]["term"]
        if fsn != r["object_label"]:
            print(f"LABEL    {r['subject_id']} -> {oid}: file='{r['object_label']}' server='{fsn}'"); bad += 1
    nomatch = sum(1 for r in rows if r["object_id"] == "sssom:NoTermFound")
    print(f"{len(rows)} rows, {checked} SNOMED objects checked ({len(cache)} distinct), "
          f"{nomatch} NoTermFound, {bad} problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
