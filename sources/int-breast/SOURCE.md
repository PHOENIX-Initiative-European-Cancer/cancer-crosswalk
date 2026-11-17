# Source: INT Breast — ECCDM availability check

- **Dataset:** Breast-cancer data of the Fondazione IRCCS Istituto Nazionale dei
  Tumori (INT, Milan), assessed attribute-by-attribute against the ECCDM logical
  models (PHOENIX pilot).
- **Spec version:** Excel workbook `INT Breast ECCDM.xlsx`, last modified
  **2026-10-30** (author: Paolo Lasalvia, INT); received 2026-11-09.
- **URL:** not publicly published — shared within the PHOENIX consortium.
- **Local copy:** `ref/INT Breast ECCDM.xlsx` (git-ignored — obtain from the PHOENIX consortium)
- **Extractor:** `scripts/extract_int_breast.py`.
- **Result:** `elements.csv` — 68 ECCDM attribute rows with the normalised INT
  presence flag (yes / no / partial) and the raw local format; `values.csv` —
  276 local codes parsed out of the `Format` column, id scheme
  `intbr:<Model>.<Attribute>.<list>.<code>` (17 value lists).
- **Mapping:** `mappings/int-breast__values__to__snomed.sssom.tsv` — code-level
  mapping of the 276 local codes (plus the four systemic-therapy variables) to
  SNOMED CT International Edition 2026-10-01, built by
  `scripts/build_int_breast_snomed_mapping.py` from a curated table and checked
  by `scripts/verify_snomed_mapping.py` against the local Snowstorm. 280 rows:
  154 exact, 88 close, 16 broad, 1 narrow, 21 `sssom:NoTermFound`. All rows
  `proposed`, pending clinical review by INT.
- **Publisher / terms:** INT Milan — internal working document, not for redistribution.

## Structure
- One sheet per ECCDM logical model (11 sheets: CancerPatient,
  CancerConditionAtDiagnosis, CancerStage, Imaging, LastFollowUp,
  ClinicalCancerProgression, Surgery, ActiveSurveillance, Radiotherapy,
  SystemicTreatment, OverallCancerTreatmentResponse) plus a `New Variables`
  sheet (wishlist: Laterality, Receptors).
- Columns: `Attribute`, `Description`, `Cardinality`, `Datatype`, `Note(s)`,
  `Vocabulary/Values` (ECCDM side) and `Presence`, `Format` (INT side: whether
  the INT breast data warehouse holds the element, and in which local coding).

## Notes
- Unlike the other spokes this is **not an independent source vocabulary**: the
  rows *are* the ECCDM elements, annotated with INT-side availability. It is
  therefore best read as a hub-side feasibility matrix (hub → local) rather than
  as a dataset to be mapped onto the hub.
- `ActiveSurveillance` (4 rows, all marked not present) is **not applicable to
  breast cancer** and should be excluded from gap counts, not read as a gap.
- Rough availability (excluding ActiveSurveillance): 62 of 68 attribute rows
  marked present. Genuine gaps: `CancerPatient.SexAtDiagnosis`,
  `LastFollowUp.CauseOfDeath` / `DeathDate`, `Surgery.Intent`,
  `SystemicTreatment.Intent`.
- Local codings in `Format` (numeric value lists for grade, sex, imaging type,
  staging examinations, surgery, radiotherapy type/site, follow-up events,
  systemic-therapy status) are the material for the SNOMED mapping above.
- The CancerStage sheet carries two blocks (older `Value` model, current
  `Stage.Code`/`Stage.Value`); repeated attributes keep the later row, the cT/cN
  value lists hang on `CancerStage.Value`.

## What the SNOMED mapping shows (2026-11-16)
- **Clean:** sex, comorbidities, body sites (imaging and lateralised radiotherapy
  sites), the 36 M-staging examinations, most breast surgery procedures, the
  cT/cN categories (UICC qualifier values; AJCC twins noted).
- **Modelling mismatches surfaced, not terminology gaps:**
  - INT lists the *surgical procedure* under `Surgery.BodySite` because ECCDM
    Surgery has no procedure-type attribute (hub gap, marked
    `(no ECCDM slot)`).
  - `Radiotherapy.Intent` codes mix intent (palliative) with setting
    (adjuvant) and add "cytoreductive", which ECCDM's Definitive|Palliative
    cannot hold.
  - The follow-up event list (21 codes) mixes vital status, disease status,
    recurrence/metastasis events and surgery; `Lost to follow-up` has no hub
    value because ECCDM VitalStatus is Alive|Dead.
  - The systemic-therapy variables are workflow statuses (ongoing/completed at
    INT vs elsewhere, refused, scheduled); they belong in FHIR
    `Procedure.status`/`statusReason`, not in a SNOMED-coded type.
  - Mixed grades "I-II" / "II-III", "Microcalcifications" as a cT value and
    "In situ" as an N value have no SNOMED equivalent and should be queried
    with INT.
- **Wishlist sheet** (Laterality, Receptors) matches gaps other spokes report.

## Pointer: INT's own variable inventory
- The workbook does not inventory INT's data-warehouse variables, so INT can only
  be analysed hub-side (`scripts/hub_matrix.py`, `docs/hub-matrix.md`).
- Public description of the underlying registry: Baili P, Torresani M, Agresti R,
  et al. *A breast cancer clinical registry in an Italian comprehensive cancer
  center: an instrument for descriptive, clinical, and experimental research.*
  Tumori 2015;101(4):440-446, https://doi.org/10.5301/tj.5000341 (paywalled;
  no variable list found online, 2026-11-16).
- To make INT a full spoke, request the DWH data dictionary for breast
  (variable name, description, value range) from INT (Paolo Lasalvia).
