# Source: Senologie-Datenkranz (SenologieOnFHIR)

- **Dataset:** Senologie-Datenkranz — the breast-cancer dataset of the DKG-certified
  breast centres (DE), modelled in the SenologieOnFHIR project.
- **Version:** logical model `bih-lm-senologie-complete.fsh` (FSH source), as in
  SenologieOnFHIR IG **0.10.0**; file last changed in commit `b41b253dc`
  (2026-10-09, CRMI ruleset insert only — no element changes). Re-extraction
  verified 2026-11-16: identical 299 elements on `main` and all feature branches.
- **URL / IG:** https://bih-cei.github.io/SenologieOnFHIR/
- **Local source:** `~/code/fhir-profiling/SenologieOnFHIR/input/fsh/bih-lm-senologie-complete.fsh`
  (read-only; not vendored into this repo).
- **Extractor:** `scripts/extract_senologie_vocab.py` (parses the FSH logical model,
  including nested BackboneElement paths).
- **Result:** `elements.csv` — 299 elements, id scheme `senol:<Model>.<path>`.
- **Value sets:** `valuesets.csv` — the 79 ValueSets of the SenologieOnFHIR IG with the
  code systems they draw from (scan of `input/fsh/**/*.fsh`, 2026-11-17, by
  `scripts/snomed_coverage.py --scan-senologie`). The logical model itself carries no
  bindings; the value sets are the IG's terminology layer.
- **Publisher / terms:** BIH-CEI (Berlin Institute of Health) / Deutsche
  Krebsgesellschaft — see the SenologieOnFHIR IG.

## Notes
- The richest breast spoke: Pathologie section = 110 of 299 elements. Captures
  Nottingham/DCIS grading, ER/PR (IRS/Allred), HER2-low, PD-L1 (CPS/TPS/IC),
  6-direction resection margins, BI-RADS/ACR, gene-expression tests, and the
  tumour board (Tumorkonferenz, 17 elements — an inverse gap: ECCDM has no MDO
  model).
- Disambiguates pre/post-op findings via specimen type (`Praeparat.Art`) rather
  than separate named fields; the crosswalk `source_context` uses histological
  entity (invasiv / dcis) instead.
