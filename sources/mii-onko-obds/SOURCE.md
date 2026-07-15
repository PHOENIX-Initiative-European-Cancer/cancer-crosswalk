# Source: MII Onkologie / oBDS

- **Dataset:** onkologischer Basisdatensatz (oBDS) — the mandatory German
  cancer-registry reporting dataset (and the basis of the MII Modul Onkologie).
- **Spec version:** oBDS XML schema **v3.0.5** (dated 2025-09-22).
- **URL:** https://www.basisdatensatz.de/xml/oBDS_v3.0.5.xsd
- **Local copy:** `ref/oBDS_v3.0.5.xsd` (git-ignored — download from the URL above)
- **Extractor:** `scripts/extract_obds_vocab.py` (walks every `xs:element`).
- **Result:** `elements.csv` — 422 elements, id scheme `obds:<ComplexType>.<element>`.
- **Publisher / terms:** Gesellschaft der epidemiologischen Krebsregister in
  Deutschland (GEKID) / basisdatensatz.de — see publisher for licensing.

## Notes
- CURIE prefix `obds:` is minted for this crosswalk (oBDS elements have no
  published per-element IRIs).
- oBDS carries several coding systems (ICD-10-GM, ICD-O-3, OPS, ATC, UICC, and
  oBDS-specific code lists); recorded in `subject_terminology`. The value/code
  layer is not yet mapped.
