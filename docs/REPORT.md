# cancer-crosswalk — short report

**What.** An SSSOM-based crosswalk and gap analysis of four cancer datasets
against the **HL7 Europe Cancer Common Data Model (ECCDM)** as a common hub. Not
an Implementation Guide — an analysis that makes correspondences and gaps
explicit and machine-readable.

## Approach

- **Hub-and-spoke.** ECCDM is the hub (68 elements / 11 logical models, extracted
  from the IG's FSH). Each source is a spoke mapped *to* the hub → *n* mapping
  sets, not *n×n*.
- **SSSOM** (mapping-commons): `subject (source) → predicate → object (ECCDM)`,
  SKOS predicates (exact/close/broad/narrow/related), `semapv` justification,
  confidence. Extension columns added: `subject_terminology`, `mapping_cardinality`,
  `element_kind` (collected/calculated), `source_context` (collision resolver),
  `review_status`. All sets validate with the official `sssom` toolkit.

## Sources (spokes)

| spoke | elements | origin |
|---|---|---|
| oBDS (DE registry) | 422 | official XSD 3.0.5 |
| NABON (NL breast) | 314 | ART-DECOR Excel |
| B1MG (EU minimal) | 140 | 1+MG-MDC, Zenodo |
| Senologie (DE breast) | 299 | `bih-lm-senologie` FSH |

## Key findings

1. **Hub coverage 43/68 (63 %)** — all 11 models mapped across all 4 spokes
   (148 proposed rows). But **source-side coverage is only 8–24 %**: the vast
   majority of each dataset's fields have no ECCDM home.
2. **Granularity asymmetry.** Specialised breast datasets (Senologie, NABON) map
   mostly *narrower* than the hub (finer granularity); the minimal dataset (B1MG)
   maps *broader* (coarser); the registry (oBDS) sits closest to the hub. The
   common/minimal models are, by construction, coarser than a specialised one.
3. **ECCDM cannot express breast specificity.** The breast-specific content —
   ER/PR/HER2, BI-RADS, Nottingham grading detail, sentinel nodes, molecular
   tests — has **no hub field**. It is invisible in a hub-indexed view. Example:
   0 of 13 oBDS breast-module fields are mappable.
4. **The missing content clusters into candidate *Ergänzungsmodule*** (1037
   unmapped source fields), classifiable by how ECCDM *could* carry them:
   - **by-reference** (Pathologie-Detail 117, Biomarker 53, BI-RADS 44, …) —
     needs an evidence hook + an Observation/Finding model; mostly
     **data-dictionary / value-set** work, not new structure.
   - **new-module** (Tumorkonferenz / MDO 40) — a genuinely new hub model.
   - **out-of-scope** (admin, biobank/genomics infrastructure).
5. **Calculated values** (UICC stage, Gleason score, Gesamtbeurteilung) are
   derived, not collected; ECCDM lacks a `derivedFrom`/provenance axis to mark
   them — a further hub gap (flagged `element_kind=calculated`).

## Deliverables (in `docs/`)

- `overview.png` — headline: (A) model-level hub coverage, (B) Ergänzungsmodule.
- `hub-spoke.png` — per-source predicate profile (the granularity asymmetry).
- `coverage-heatmap.png` — element-level drill-down (68 × 4).
- `ergaenzungsmodule.md` — the extension-module wishlist with carriage class.
- `methodology.md` — mapping conventions.

## Status & limits

All 148 mappings are `proposed` — **no domain-expert review yet**. Terminology
(code-level) mapping deferred. `source_context` for one model (durchstich) is
richly populated; the fan-out rows are lighter. Panel B still has ~564
unclustered unmapped fields to triage.

## Recommendation for HL7 EU

ECCDM works as a generic *semantic spine* but, for a breast-cancer effort, needs
**extension modules attached by evidence-reference** — largely a
data-dictionary/Library exercise (Observation catalogues + computable
derivations) plus one new structural model (tumour board / MDO). The crosswalk
now quantifies exactly what those modules must contain.
