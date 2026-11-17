#!/usr/bin/env python3
"""Extract the INT Breast ECCDM availability workbook into CSV.

Reads ``sources/int-breast/ref/INT Breast ECCDM.xlsx`` (INT Milan, PHOENIX
pilot; one sheet per ECCDM logical model with INT-side ``Presence`` /
``Format`` columns) and emits

* ``sources/int-breast/elements.csv`` — one row per ECCDM attribute as INT
  annotated it (id ``intbr:<Model>.<Attribute>``), with the normalised
  presence flag and the raw local-format text;
* ``sources/int-breast/values.csv`` — one row per *local code* parsed out of
  the ``Format`` cells (id ``intbr:<Model>.<Attribute>.<list>.<code>``).
  These local value lists are the material for the SNOMED CT mapping in
  ``mappings/int-breast__values__to__snomed.sssom.tsv``.

The CancerStage sheet carries two blocks (the older ``Value`` model and the
current ``Stage.Code``/``Stage.Value`` model). Attributes repeated across the
blocks keep the later row; the TNM value lists hang on ``CancerStage.Value``.

Usage:
    python scripts/extract_int_breast.py [--xlsx FILE] [--out-dir DIR]
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_XLSX = REPO / "sources" / "int-breast" / "ref" / "INT Breast ECCDM.xlsx"
DEFAULT_OUT = REPO / "sources" / "int-breast"

# Short keys for the named value lists (heading line in the Format cell -> key).
LIST_KEYS = {
    "Clinical T stage (TNM) based on imaging findings": "cT_imaging",
    "Clinical T stage (TNM) based on mammography": "cT_mammo",
    "Clinical nodal stage N (TNM)": "cN",
    "Mammography": "mammography",
    "Ultrasound": "ultrasound",
    "j-th staging examination performed to determine M stage at diagnosis": "m_staging_exam",
    "Type of Follow-Up, j-th event (j = 1, ..., n)": "followup_event",
    "Information on Surgical Procedure j": "procedure",
    "Type of Radiotherapy, Phase j": "rt_type",
    "Site k of Phase j (k = 1,2; j = 1, ...)": "rt_site",
    "Status of neoadjuvant chemotherapy in relation to surgery": "neoadj_chemo_status",
    "Status of adjuvant chemotherapy, phase j": "adj_chemo_status",
    "Hormone therapy status, phase j": "hormone_status",
    "Target therapy status, phase j": "target_status",
    "Available for": "comorbidity",
}

CODE_LINE = re.compile(r"^(\d+)\s*=?\s*(.+?)\s*$")
PAREN_LIST = re.compile(r"\(\s*(\d+\s*=.*)\)\s*\.?\s*$", re.S)


def norm_presence(p: str) -> tuple[str, str]:
    p = (p or "").strip()
    low = p.lower()
    if not p:
        return "", ""
    if low == "yes":
        return "yes", ""
    if low == "no":
        return "no", ""
    if low.startswith("yes"):
        return "partial", p
    return "unclear", p


def list_key(heading: str) -> str:
    h = heading.strip().rstrip(":").strip()
    h = re.sub(r"^Various variables:\s*", "", h)
    if h in LIST_KEYS:
        return LIST_KEYS[h]
    return re.sub(r"[^A-Za-z0-9]+", "_", h).strip("_").lower()[:40]


def parse_values(fmt: str) -> list[tuple[str, str, str]]:
    """Return (list_key, code, label) triples parsed from a Format cell."""
    if not fmt:
        return []
    out: list[tuple[str, str, str]] = []
    # Comma list: "Available for: A, B, C"
    m = re.match(r"^Available for:\s*(.+)$", fmt.strip(), re.S)
    if m:
        for i, lab in enumerate(x.strip() for x in m.group(1).split(",")):
            if lab:
                out.append(("comorbidity", str(i + 1), lab))
        return out
    key = "code"
    uncoded: list[str] = []
    for raw in fmt.splitlines():
        line = raw.strip()
        if not line:
            continue
        pm = PAREN_LIST.search(line)
        if pm:  # "(0 = a; 10 = b; ...)"
            for part in pm.group(1).split(";"):
                cm = CODE_LINE.match(part.strip())
                if cm:
                    out.append((key, cm.group(1), cm.group(2)))
            continue
        cm = CODE_LINE.match(line)
        if cm and not line.endswith(":"):
            out.append((key, cm.group(1), cm.group(2).strip('"').strip()))
            continue
        if line.startswith('"'):  # follow-up list: a quoted label without code
            out.append((key, "", line.strip('"').strip()))
            continue
        # anything else is a heading (or a plain uncoded label)
        if "=" in line and "(" not in line.split("=")[0]:
            continue
        key = list_key(line)
        uncoded.append(line)
    if not out and len(uncoded) >= 3:
        # plain label list (Imaging.BodySite): every line is a value
        return [("site", "", lab) for lab in uncoded]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    wb = openpyxl.load_workbook(args.xlsx, read_only=True, data_only=True)
    elements: dict[str, dict] = {}
    values: list[dict] = []
    seen_values: set[str] = set()
    for ws in wb.worksheets:
        if ws.title == "New Variables":
            continue
        for r in ws.iter_rows(values_only=True):
            if not r or not r[0] or r[0] == "Attribute":
                continue
            attr = str(r[0]).strip()
            cells = [("" if c is None else str(c).strip()) for c in (list(r) + [None] * 8)[:8]]
            presence, note = norm_presence(cells[6])
            eid = f"intbr:{ws.title}.{attr}"
            elements[eid] = {
                "id": eid, "model": ws.title, "element": attr,
                "cardinality": cells[2], "datatype": cells[3],
                "presence": presence, "presence_note": note,
                "local_format": cells[7].replace("\n", " / "),
                "definition": cells[1],
            }
            for key, code, label in parse_values(cells[7]):
                slug = code or re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_").lower()
                vid = f"{eid}.{key}.{slug}"
                if vid in seen_values:
                    continue  # CancerStage sheet repeats its block
                seen_values.add(vid)
                values.append({
                    "id": vid, "model": ws.title, "element": attr,
                    "value_list": key, "code": code, "label": label,
                })

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("elements.csv", list(elements.values())), ("values.csv", values)):
        p = args.out_dir / name
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f"Wrote {p}: {len(rows)} rows")
    from collections import Counter
    for k, n in Counter(v["value_list"] for v in values).most_common():
        print(f"  {k}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
