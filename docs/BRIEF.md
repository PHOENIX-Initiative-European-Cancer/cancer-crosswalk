# Design brief — cancer-crosswalk

*A self-contained problem statement to hand to a fresh (design) session.*

## In one line

A machine-readable crosswalk that maps four cancer datasets onto the HL7 Europe
Common Cancer Data Model (ECCDM) to reveal, quantitatively, what a shared cancer
hub can and cannot represent — and what a breast-cancer extension would need.

## The problem

European cancer data lives in many national/domain standards. To make them
comparable (registries, EHDS secondary use), HL7 Europe proposes ECCDM as a
common hub. **But is a generic pan-cancer hub adequate for a breast-cancer use
case?** We built the crosswalk to answer this with evidence rather than opinion.

What we found is a **two-sided mismatch** that is the core design tension:

- ECCDM (68 elements, 11 models) is a thin *generic spine*. It covers the common
  backbone (63 % of its own elements get mapped) but only **8–24 % of each
  source dataset** — the rest has no hub home.
- The uncovered majority is **breast-specific detail** (ER/PR/HER2, BI-RADS,
  grading detail, molecular tests, tumour-board decisions). It is *invisible* in
  a hub-indexed view, which makes the hub look deceptively "complete."
- That missing content is structured: it clusters into a handful of candidate
  **extension modules**, most of which are *data-dictionary* work (coded
  observations + value sets attached by evidence-reference), not new structure.

## Current state (what exists in the repo)

- **Hub:** `hub/eccdm/elements.csv` — 68 elements / 11 models, extracted from the
  ECCDM IG.
- **Spokes:** `sources/*/elements.csv` — oBDS 422, NABON 314, B1MG 140,
  Senologie 299 (each extracted from its official source).
- **Mappings:** `mappings/*__to__eccdm.sssom.tsv` — 148 SSSOM rows, valid,
  **all `proposed` (unreviewed)**. Columns include SKOS predicate, confidence,
  cardinality, `element_kind` (collected/calculated), `source_context`.
- **Analysis + figures:** `scripts/*` regenerate everything;
  `docs/overview.png` (coverage + extension modules), `docs/hub-spoke.png`
  (predicate profile), `docs/coverage-heatmap.png` (element drill-down),
  `docs/ergaenzungsmodule.md` (extension wishlist), `docs/REPORT.md/.pdf`.

## The design questions to play through

1. **Architecture** — how should ECCDM carry breast specificity? The candidate
   answer: keep the generic spine, add **extension modules by evidence-reference**
   (a generic evidence/detail reference + an Observation/Finding model on the
   hub) + a `derivedFrom` axis for calculated values (UICC, Gleason). Is this the
   right shape? What are the alternatives (e.g. mCODE-style, which ECCDM rejected)?

2. **Communication / visualization** — the analysis is inherently two-sided (hub
   coverage *and* source-side gaps). Current figures work but each answers one
   question. **What is the single most legible way to show "generic spine +
   breast extension modules" to a standards working group?** (A bipartite flow /
   Sankey from sources → {hub models, extension modules} is one untried idea.)

3. **Scope / method** — mappings are element-level and unreviewed; terminology
   (code-level) mapping is deferred; ~564 unmapped source fields are still
   untriaged. What is the right next slice to make the argument watertight?

## Key facts to reason with

- Hub coverage 43/68 (63 %); source coverage 8–24 %.
- Granularity asymmetry: specialised breast datasets map *narrower* than the hub;
  the minimal dataset maps *broader*; the registry sits closest.
- 0 of 13 oBDS breast-module fields are mappable to ECCDM.
- Extension clusters: Pathology detail 117, Biomarkers 53, BI-RADS 44, MDO 40
  (new module), molecular tests 26 — mostly data-dictionary, one new model.

*Full detail: `docs/REPORT.md`. Repo: local git, no remote yet.*
