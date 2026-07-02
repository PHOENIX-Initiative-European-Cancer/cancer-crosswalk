# Source: B1MG — 1+MG Minimal Dataset for Cancer

- **Dataset:** 1+Million Genomes Minimal Dataset for Cancer (1+MG-MDC) — an EU,
  registry-oriented *minimal* dataset (138 items across 8 conceptual domains).
- **Version:** `1+MG-MDC_01.xlsx` (with legend `1+MG-MDC_01_Legend.docx`).
- **DOI:** https://doi.org/10.5281/zenodo.10784601 (Zenodo record 10784601).
- **Publication:** Nature Genetics, https://www.nature.com/articles/s41588-024-01721-x
- **Local copy:** `ref/1+MG-MDC_01.xlsx`, `ref/1+MG-MDC_01_Legend.docx`
- **Extractor:** `scripts/extract_b1mg_vocab.py`.
- **Result:** `elements.csv` — 140 items, id scheme `b1mg:<item-number>`.
- **Publisher / terms:** 1+Million Genomes / B1MG consortium (Horizon 2020,
  grant 951724). Zenodo record is CC BY.

## Notes
- Genomics-research minimal dataset, **not** a clinical registry: its largest
  domain (SAMPLE, 45 items — biobank/genomics metadata) has no ECCDM counterpart
  (an inverse gap, out-of-scope for the clinical hub).
- 140 (not 138) rows because several item names repeat across sample sub-types,
  each with its own numeric id.
