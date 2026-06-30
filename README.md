# cancer-crosswalk

SSSOM-based crosswalk and **gap analysis** of cancer datasets against the
**HL7 Europe Cancer Common Data Model (ECCDM)** as the common hub.

This is an *analysis* repository, not an Implementation Guide. It maps the data
elements of several national / domain cancer datasets onto one shared reference
model and lets the gaps and semantic mismatches fall out of the mapping coverage.

## Approach: hub-and-spoke

ECCDM is the **hub**. Every source dataset is a **spoke** mapped *to* the hub.
This keeps the number of mapping sets at *n* (one per source) instead of *n×n*,
and makes the hub the lingua franca for comparison and gap reporting.

```
   MII Onko / oBDS ─┐
   Senologie-DK   ──┤
   B1MG CMD       ──┼──►  ECCDM (hub)
   NABON Mamma    ──┘
```

Mappings use [SSSOM](https://github.com/mapping-commons/SSSOM) (Simple Standard
for Sharing Ontological Mappings): a TSV of `subject → predicate → object` with
embedded YAML metadata, SKOS predicates, `semapv` justifications and confidence.

## Layout

| path | what |
|---|---|
| `hub/eccdm/elements.csv` | the hub vocabulary — 68 ECCDM logical-model elements (generated) |
| `mappings/<source>__to__eccdm.sssom.tsv` | one SSSOM mapping set per source dataset |
| `sources/<source>/` | provenance + extracted element list per source |
| `scripts/extract_eccdm_hub.py` | regenerate the hub from the cancer-common FSH models |
| `scripts/coverage.py` | gap analysis: hub coverage per source + uncovered elements |
| `prefixes.yaml` | shared CURIE map (prefixes are minted for this crosswalk) |
| `docs/methodology.md` | mapping conventions (direction, predicates, confidence) |
| `docs/datasets.md` | the source datasets: versions, licenses, where to get them |

## Usage

```bash
python3 scripts/extract_eccdm_hub.py   # (re)build hub/eccdm/elements.csv
python3 scripts/coverage.py            # gap analysis to stdout
python3 scripts/coverage.py --md       # ... as Markdown
```

## Status

| source | mapping rows | state |
|---|---|---|
| MII Onko / oBDS | 13 | seeded (high-confidence items only) |
| Senologie-Datenkranz | 0 | template |
| B1MG CMD | 0 | template |
| NABON Mammacarcinoom | 0 | template |

Hub coverage so far: **19 %** (13 / 68 elements). See `scripts/coverage.py`.

## Optional next step: validate with sssom-py

The mapping sets are plain SSSOM and can be linted/validated/converted with the
official toolkit:

```bash
pip install sssom
sssom validate mappings/mii-onko-obds__to__eccdm.sssom.tsv
sssom convert mappings/*.sssom.tsv -O owl   # or json, rdf, ...
```
