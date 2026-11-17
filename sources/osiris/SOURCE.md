# Source: OSIRIS (inter-SiRIC oncology minimum data set, FR) — PARKED

- **Status:** extracted and mapping drafted, but **not wired into the analysis**
  (not in `inverse_gaps.SOURCES`, no file under `mappings/`, no prefix). Reason:
  INCa is not an HL7 member, so OSIRIS is not a stakeholder-backed input to the
  HL7 Europe ECCDM discussion. Re-enable by (1) adding `"osiris":
  "sources/osiris/elements.csv"` to `SOURCES` in `scripts/inverse_gaps.py`,
  (2) moving `osiris__to__eccdm.sssom.tsv.draft` to `mappings/` without the
  `.draft` suffix, (3) adding `osiris: "https://github.com/siric-osiris/OSIRIS/data-element/"`
  to `prefixes.yaml`, (4) adding the source to the label maps in `overview.py`,
  `hubspoke.py`, `outside_hub.py`, `hub_target.py`.
- **Dataset:** OSIRIS — event-based minimum data set for clinical, omics and
  imaging data sharing in oncology, from the French SiRIC network / Institut
  National du Cancer.
- **Spec version:** `data/DataElementConcept.tsv` of
  https://github.com/siric-osiris/OSIRIS at `master` commit `e76142b`
  (2022-10-20; includes the imaging / radiomics extension). FHIR rendering:
  IG `inca.fhir.uv.osiris` 1.1.0 (trial implementation, 2025-04),
  https://ig-osiris.cancer.fr/ig/osiris/ — profiles only, no logical model.
- **URL:** https://github.com/siric-osiris/OSIRIS (data dictionary, ISO 11179
  style) · paper: JCO CCI 2021, https://pmc.ncbi.nlm.nih.gov/articles/PMC8140800
- **Local copy:** `ref/DataElementConcept.tsv`, `ref/ConceptualDomain.tsv`,
  `ref/ModeleCliniqueOSIRIS-english_version.pdf` (git-ignored).
- **Extractor:** `scripts/extract_osiris_vocab.py`.
- **Result:** `elements.csv` — 218 data element concepts, id scheme
  `osiris:<ObjectClass>_<Property>`; columns include ISO id, object class and
  a coarse domain (patient / tumour / treatment / sample / omics / imaging).
- **Mapping draft:** `osiris__to__eccdm.sssom.tsv.draft` — 34 proposed rows
  (patient, follow-up, diagnosis, grade, stage / TNM, response, treatment
  dates, imaging modality and body part). Unreviewed.
- **Publisher / terms:** SiRIC / INCa; repository has no explicit licence file.

## Notes
- 86 of 218 items are DICOM acquisition parameters and IBSI radiomics
  settings, 71 are omics (variant / CNV / fusion / expression / annotation);
  only ~60 are clinical items comparable to the other spokes.
- Treatment is one generic class (type, dates, line, trial context); modality
  split only through the type value set — same coarseness as B1MG.
