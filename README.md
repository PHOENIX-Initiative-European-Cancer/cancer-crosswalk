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
- **`docs/overview.png`** — the headline figure (hub coverage + extension modules).

## Layout

| path | what |
|---|---|
| `hub/eccdm/elements.csv` | the hub vocabulary — 68 ECCDM logical-model elements (generated) |
| `mappings/<source>__to__eccdm.sssom.tsv` | one SSSOM mapping set per source dataset |
| `sources/<source>/` | `SOURCE.md` (provenance) + `elements.csv` (extracted vocabulary) + `ref/` (the fetched spec) |
| `scripts/extract_*.py` | rebuild each vocabulary from its official source |
| `scripts/coverage.py` | hub coverage per source + uncovered elements |
| `scripts/inverse_gaps.py` | source-side gaps clustered into candidate extension modules |
| `scripts/overview.py` · `hubspoke.py` · `heatmap.py` | figures |
| `prefixes.yaml` | shared CURIE map (prefixes are minted for this crosswalk) |
| `docs/methodology.md` | mapping conventions (direction, predicates, confidence, extension columns) |
| `docs/datasets.md` | the source datasets: versions, provenance |
| `docs/extension-modules.md` | inverse-gap wishlist (what ECCDM would need) |

## Reproduce

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install sssom matplotlib openpyxl

# rebuild vocabularies from the official sources (specs are in sources/*/ref/)
python3 scripts/extract_eccdm_hub.py
for s in obds nabon b1mg senologie; do python3 scripts/extract_${s}_vocab.py; done

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

Hub coverage: **63 %** (43 / 68 elements). **All 148 mappings are `proposed`
(not expert-reviewed).** Terminology/code-level mapping is deferred. See
`docs/REPORT.md` for findings and limitations.

## Sources & attribution

Each spoke's provenance (spec version, URL, extractor) is in
`sources/<source>/SOURCE.md`. This repository stores only *derived element
inventories* and *correspondence statements* — not the full source specifications.
Source datasets remain under their publishers' terms; ECCDM (the hub) is published
by HL7 Europe.

## License

This repository's own content (mappings, vocabularies, scripts, docs, figures) is
licensed **CC BY 4.0** — see [`LICENSE`](LICENSE). The analysis is a work product,
**not** an authoritative or normative mapping.
