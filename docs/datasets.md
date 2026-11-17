# Source datasets

| key | dataset | scope | jurisdiction | local copy |
|---|---|---|---|---|
| `eccdm` (hub) | HL7 Europe Cancer Common Data Model | pan-cancer common model | EU | `../cancer-common` |
| `mii-onko-obds` | MII Modul Onkologie + oBDS Basisdatensatz | pan-cancer, registry | DE | `../kerndatensatzmodul-onkologie` |
| `senologie-datenkranz` | Senologie-Datenkranz (DKG-zertifizierte Brustzentren) | breast | DE | `../SenologieOnFHIR` |
| `b1mg-cmd` | B1MG / EU Cancer Minimal Dataset | pan-cancer, minimal | EU | — |
| `nabon-mammacarcinoom` | NABON Informatiestandaard Mammacarcinoom | breast | NL | — |
| `int-breast` | INT Milan breast dataset — ECCDM availability check | breast | IT | `sources/int-breast/ref/` |
| `esmo-breast` | ESMO Clinical Practice Guidelines, early and metastatic breast cancer — *requirement source* | breast | EU | `sources/esmo-breast/ref/` |

## ECCDM (hub)

- HL7 Europe Cancer Common Data Model. Build: https://build.fhir.org/ig/hl7-eu/cancer-common/index.html
- Source: `hl7-eu/cancer-common`. Local clone: `../cancer-common`.
- Hub = the 11 LogicalModels under `input/fsh/models/`. Regenerate with
  `scripts/extract_eccdm_hub.py`.

## MII Onkologie / oBDS

- MII Modul Onkologie (FHIR) largely incorporates the **oBDS** (onkologischer
  Basisdatensatz) — the mandatory German cancer-registry reporting dataset.
- Local clone: `../kerndatensatzmodul-onkologie`.
- The seed mapping uses `obds:` element ids for the registry-level items.

## Senologie-Datenkranz

- DKG / certified breast centres dataset ("Datenkranz"). Breast-specific,
  richer than oBDS for mamma.
- Local work: `../SenologieOnFHIR`.

## B1MG Cancer Minimal Dataset

- Beyond 1 Million Genomes — EU cancer minimal dataset (registry-oriented,
  intentionally small core).
- No local copy yet — to be sourced.

## NABON Mammacarcinoom

- Dutch breast cancer information standard.
- https://www.nabon.nl/informatiestandaard/
- No local copy yet — to be sourced.

## INT Breast (ECCDM availability check)

- Fondazione IRCCS Istituto Nazionale dei Tumori, Milan — breast-cancer data
  warehouse assessed against the ECCDM logical models (PHOENIX pilot).
- Workbook `INT Breast ECCDM.xlsx` (2026-10-30), one sheet per ECCDM model with
  INT-side `Presence` / `Format` columns. Not public; see `sources/int-breast/SOURCE.md`.
- Structurally a hub → local feasibility matrix, so it is not a spoke in the
  element-level crosswalk. Instead its local value lists are mapped at *code
  level* to SNOMED CT: `scripts/extract_int_breast.py` →
  `sources/int-breast/{elements,values}.csv`;
  `scripts/build_int_breast_snomed_mapping.py` →
  `mappings/int-breast__values__to__snomed.sssom.tsv` (280 rows, verified
  against SNOMED CT INT 2026-10-01 by `scripts/verify_snomed_mapping.py`).

## ESMO breast cancer guidelines (requirement source)

- Not a dataset: the data points that recommendations depend on, read from
  Loibl et al. 2024 (early breast cancer, Ann Oncol 35:159-182) and
  de Azambuja et al. 2026 (metastatic breast cancer, Ann Oncol 37:1203-1219,
  superseding Gennari et al. 2021). See `sources/esmo-breast/SOURCE.md`.
- 111 consolidated data points with role (diagnostic / prognostic / predictive /
  treatment record / monitoring), value domain and the decision each drives;
  77 SSSOM rows to the hub; `docs/esmo-datapoints.md` reports hub home,
  carriage class, INT availability and which standards carry each item.

## Provenance discipline

Each `sources/<key>/` folder should hold: the extracted `elements.csv` (the
spoke vocabulary), and a `SOURCE.md` recording exact version/date/URL of the
spec the elements were read from, so every mapping row is traceable.
