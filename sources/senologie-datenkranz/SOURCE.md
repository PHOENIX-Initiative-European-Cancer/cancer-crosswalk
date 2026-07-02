# Source: Senologie-Datenkranz (SenologieOnFHIR)

- **Dataset:** Senologie-Datenkranz — the breast-cancer dataset of the DKG-certified
  breast centres (DE), modelled in the SenologieOnFHIR project.
- **Version:** logical model `bih-lm-senologie-complete.fsh` (FSH source).
- **URL / IG:** https://bih-cei.github.io/SenologieOnFHIR/
- **Local source:** `~/code/fhir-profiling/SenologieOnFHIR/input/fsh/bih-lm-senologie-complete.fsh`
  (read-only; not vendored into this repo).
- **Extractor:** `scripts/extract_senologie_vocab.py` (parses the FSH logical model,
  including nested BackboneElement paths).
- **Result:** `elements.csv` — 299 elements, id scheme `senol:<Model>.<path>`.
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
