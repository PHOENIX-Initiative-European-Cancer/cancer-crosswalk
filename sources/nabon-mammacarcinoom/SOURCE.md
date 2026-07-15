# Source: NABON Informatiestandaard borstkanker

- **Dataset:** NABON breast-cancer information standard (NL) — the multidisciplinary
  team (MDO) reporting standard for mammacarcinoom.
- **Spec version:** Excel export dated **2020-11-12**; ART-DECOR project prefix
  `onco-mamma-new-`.
- **URL:** https://www.nabon.nl/standaardisatie-epd/
  (Excel: https://www.nabon.nl/wp-content/uploads/2020/11/Informatiestandaard-borstkanker-12-nov-2020.xlsx)
- **Local copy:** `ref/Informatiestandaard-borstkanker-12-nov-2020.xlsx` (git-ignored — download from the URL above)
- **Extractor:** `scripts/extract_nabon_vocab.py` (parses `onco-mamma-new-dataelement-*` rows).
- **Result:** `elements.csv` — 314 data elements, id scheme `nabon:dataelement-<N>`.
- **Publisher / terms:** NABON / Nictiz — standard offered via ART-DECOR.

## Notes
- Breast-specific and **MDO-report-centric**: elements are indexed by treatment
  phase (preoperatief / postoperatief / neoadjuvant / metastase / recidief),
  captured in the mapping `source_context` column.
- Value lists (SNOMED-bound `Waardelijst`s) are present but the code layer is
  not yet mapped.
