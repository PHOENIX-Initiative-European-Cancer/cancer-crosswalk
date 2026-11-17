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

## Read this first

- **`docs/REPORT.md`** (and `REPORT.pdf`) — the self-contained analysis report.
- **`docs/BRIEF.md`** — a one-page problem statement.
- **`docs/overview.png`** — the headline figure (hub coverage + extension modules). Every figure script also takes `--slide` for a landscape, larger-type version (`docs/*-slide.png`) used in the BIH deck; colours and type come from `scripts/figstyle.py` (BIH theme hues, stepped to pass the data-viz palette checks).
- **`docs/outside-hub.png`** — what lies outside the hub, per source and by category.
- **`docs/hub-target.png`** — the one-picture view: domain × distance-from-hub × fields, with the breast-specific share.
- **`docs/snomed-coverage.png`** — SNOMED CT coverage per domain where the code layer is known: INT local codes (code level) and the Senologie value sets (value-set level, cached in `sources/senologie-datenkranz/valuesets.csv`); `scripts/snomed_coverage.py`.
- **`docs/hub-matrix.png`** / `hub-matrix.md` — the 68 hub elements × mapped standards × INT Milan availability: where standards and a real data warehouse agree.
- **`docs/hub-layers-{1,2,3}.png`** — the same geometry as a slide build: one circle per source (incl. INT Breast), then the overlay, then the distance rings (`scripts/hub_layers.py`). `docs/hub-layers-pair-{1,2,3}.png` are the slide version, two circles per figure (`--stage pairs`).

## Layout

| path | what |
|---|---|
| `hub/eccdm/elements.csv` | the hub vocabulary — 68 ECCDM logical-model elements (generated) |
| `mappings/<source>__to__eccdm.sssom.tsv` | one SSSOM mapping set per source dataset (element level) |
| `mappings/int-breast__values__to__snomed.sssom.tsv` | code-level set: INT Milan local codes → SNOMED CT (280 rows, FSNs verified against Snowstorm) |
| `mappings/esmo-breast__to__eccdm.sssom.tsv` | requirement set: data points the ESMO breast guidelines depend on → ECCDM (77 rows; the rest of the 111 data points are classed by carriage in `sources/esmo-breast/elements.csv`) |
| `sources/<source>/` | `SOURCE.md` (provenance) + `elements.csv` (extracted vocabulary) + `ref/` (the fetched spec) |
| `scripts/extract_*.py` | rebuild each vocabulary from its official source (`extract_int_breast.py` also emits `values.csv`, the local code lists) |
| `scripts/build_int_breast_snomed_mapping.py` · `verify_snomed_mapping.py` | curated code table → SSSOM, and an independent FSN/active check of every `sct:` object against a Snowstorm |
| `scripts/build_esmo_source.py` | curated table of ESMO guideline data points → `sources/esmo-breast/elements.csv`, the SSSOM set above and `docs/esmo-datapoints.md` (gap report incl. INT and the four standards) |
| `scripts/coverage.py` | hub coverage per source + uncovered elements |
| `scripts/inverse_gaps.py` | source-side gaps clustered into candidate extension modules |
| `scripts/overview.py` · `hubspoke.py` · `heatmap.py` · `outside_hub.py` · `hub_target.py` · `hub_layers.py` · `hub_matrix.py` | figures (`outside_hub.py` → `docs/outside-hub.png`: outside content per source, shared by whom; `hub_target.py` → `docs/hub-target.png`: domain × carriage target diagram with breast-specific share) |
| `prefixes.yaml` | shared CURIE map (prefixes are minted for this crosswalk) |
| `docs/methodology.md` | mapping conventions (direction, predicates, confidence, extension columns) |
| `docs/datasets.md` | the source datasets: versions, provenance |
| `docs/extension-modules.md` | inverse-gap wishlist (what ECCDM would need) |
| `docs/esmo-datapoints.md` | the ESMO breast guidelines as a requirement source: which guideline-critical data points the hub carries, which are derivable, which have no home, and who carries them |

## Reproduce

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install sssom matplotlib openpyxl

# rebuild vocabularies from the official sources (specs are in sources/*/ref/)
python3 scripts/extract_eccdm_hub.py
for s in obds nabon b1mg senologie; do python3 scripts/extract_${s}_vocab.py; done
python3 scripts/extract_int_breast.py   # sources/int-breast/{elements,values}.csv

# code-level SNOMED mapping (needs a Snowstorm with SNOMED CT INT 2026-10-01, default http://localhost:8090)
python3 scripts/build_int_breast_snomed_mapping.py
python3 scripts/verify_snomed_mapping.py mappings/int-breast__values__to__snomed.sssom.tsv

# ESMO guideline data points as a requirement source (guideline texts in sources/esmo-breast/ref/)
python3 scripts/build_esmo_source.py       # sources/esmo-breast/elements.csv, mappings/esmo-breast__to__eccdm.sssom.tsv, docs/esmo-datapoints.md

# analysis + figures + validation
python3 scripts/coverage.py
python3 scripts/inverse_gaps.py
python3 scripts/overview.py            # docs/overview.png
sssom validate mappings/*.sssom.tsv
```

## Status

| source | jurisdiction / scope | elements | mapping rows |
|---|---|---|---|
| oBDS | DE · pan-cancer registry | 422 | 37 |
| NABON | NL · breast | 314 | 34 |
| B1MG | EU · pan-cancer minimal | 140 | 34 |
| Senologie | DE · breast | 299 | 43 |
| ESMO breast CPGs (requirement source) | EU · early + metastatic breast guidelines | 111 data points | 77 |

Hub coverage: **63 %** (43 / 68 elements). Of the 1,037 unmapped source
fields, 693 are clinical content ECCDM would need (14 named categories:
by-reference / extend-model / new-module) and 344 are out of scope
(administrative, registry transport, other-entity organ modules, biobank
infrastructure) — see `docs/outside-hub.png` and `docs/extension-modules.md`.
**All 148 element mappings are `proposed` (not expert-reviewed).**

Code level: the INT Milan breast workbook is not a spoke (its rows *are* the
ECCDM attributes) but carries local value lists; these 276 codes are mapped to
SNOMED CT INT 2026-10-01 in `mappings/int-breast__values__to__snomed.sssom.tsv`
(154 exact · 88 close · 16 broad · 1 narrow · 21 no SNOMED term; all
`proposed`). See `sources/int-breast/SOURCE.md` for what the mapping exposes.
See `docs/REPORT.md` for findings and limitations.

## Source references

The source specifications are **not vendored** in this repository (they remain
under their publishers' terms). Download them into `sources/<source>/ref/`
(git-ignored) to re-run the extractors. Per-source detail: `sources/<source>/SOURCE.md`.

| source | version | download |
|---|---|---|
| ECCDM (hub) | Cancer Common IG | https://build.fhir.org/ig/hl7-eu/cancer-common/ |
| oBDS | XSD v3.0.5 (2025-09-22) | https://www.basisdatensatz.de/xml/oBDS_v3.0.5.xsd |
| NABON | Informatiestandaard borstkanker (2020-11-12) | https://www.nabon.nl/wp-content/uploads/2020/11/Informatiestandaard-borstkanker-12-nov-2020.xlsx |
| B1MG | 1+MG-MDC_01 | https://doi.org/10.5281/zenodo.10784601 |
| Senologie | `bih-lm-senologie-complete.fsh` | https://bih-cei.github.io/SenologieOnFHIR/ |
| INT Breast | `INT Breast ECCDM.xlsx` (2026-10-30) | not public — PHOENIX consortium (INT Milan) |

This repository contains only *derived element inventories* and *correspondence
statements*. Source datasets remain under their publishers' terms; ECCDM (the
hub) is published by HL7 Europe.

## License

This repository's own content (mappings, vocabularies, scripts, docs, figures) is
licensed **CC BY 4.0** — see [`LICENSE`](LICENSE). The analysis is a work product,
**not** an authoritative or normative mapping.
