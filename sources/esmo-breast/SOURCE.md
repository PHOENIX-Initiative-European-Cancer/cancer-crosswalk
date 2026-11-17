# Source: ESMO Clinical Practice Guidelines — breast cancer (requirement source)

Unlike the other sources, this is not a dataset but a **requirement source**: the
data points that recommendations in the ESMO breast cancer guidelines depend on.
Mapping them to the hub answers "which of the variables a guideline-conformant
decision needs can ECCDM carry, and who else carries the rest".

- **Guidelines:**
  - Loibl S, André F, Bachelot T, et al. *Early breast cancer: ESMO Clinical
    Practice Guideline for diagnosis, treatment and follow-up.* Ann Oncol
    2024;35(2):159-182. https://doi.org/10.1016/j.annonc.2023.11.016 (Open Archive).
  - de Azambuja E, Barrios CH, Bartsch R, et al. *Metastatic breast cancer: ESMO
    Clinical Practice Guideline for diagnosis, treatment and follow-up.* Ann Oncol
    2026;37(9):1203-1219. https://doi.org/10.1016/j.annonc.2026.05.707. Supersedes
    Gennari A et al., Ann Oncol 2021;32(12):1475-1495,
    https://doi.org/10.1016/j.annonc.2021.09.019, which is kept because the 2026
    main text moves the diagnostic and staging detail into its supplement.
- **Local copies (git-ignored, `ref/`):** `ebc-2024-fulltext.txt` and
  `mbc-2026-fulltext.txt` (main text captured from the Annals of Oncology article
  pages on 2026-11-16, supplements not captured), `mbc-2021-am.pdf` / `.txt`
  (accepted manuscript from the Swansea University repository, CC BY-NC-ND).
  Publisher terms apply; download from the DOIs above.
- **Extraction:** three per-guideline tables, one row per data point with
  category, role, value domain, section, decision it drives, and a verbatim
  phrase plus line number in the local text (`ref/ebc-2024-datapoints.md`,
  190 rows; `ref/mbc-2026-datapoints.md`, 158 rows; `ref/mbc-2021-datapoints.md`,
  130 rows). Produced by LLM-assisted reading of the local texts, every row
  traceable to a line.
- **Consolidation:** `scripts/build_esmo_source.py` holds the curated table that
  merges the three extractions into one row per concept (111 data points) and
  assigns each a hub element and predicate, or a carriage class when the hub has
  no element for it.
- **Result:** `elements.csv` — 111 rows, id scheme `esmo:<Domain>.<key>`; extra
  columns `category`, `role` (diagnostic / prognostic / predictive / treatment
  record / monitoring), `value_domain`, `decision`, `guidelines`, `hub_carriage`.
- **Mapping:** `mappings/esmo-breast__to__eccdm.sssom.tsv` — 77 rows, only for
  data points with a hub element. `docs/esmo-datapoints.md` is the generated gap
  report.
- **Publisher / terms:** ESMO; the guideline texts are copyright Elsevier/ESMO.
  Only data-point names and short phrases are reproduced here.

## Notes

- Predicates follow `docs/methodology.md`: `narrowMatch` where the guideline
  needs a finer concept than the hub element carries (cT/pT/ypT as stage blocks,
  a named agent against the therapy category, pCR against the response type),
  `relatedMatch` where the item is derivable from hub elements (age, disease-free
  interval, timing of relapse relative to adjuvant therapy, prior exposure).
- Process items (patient preference, drug availability, care setting, patient
  education) are kept in the table so the count is transparent, classed `process`.
- INT's own "New Variables" sheet asks for Laterality and Receptors; both appear
  here as guideline dependencies without a hub home.
