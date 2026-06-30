# Source datasets

| key | dataset | scope | jurisdiction | local copy |
|---|---|---|---|---|
| `eccdm` (hub) | HL7 Europe Cancer Common Data Model | pan-cancer common model | EU | `../cancer-common` |
| `mii-onko-obds` | MII Modul Onkologie + oBDS Basisdatensatz | pan-cancer, registry | DE | `../kerndatensatzmodul-onkologie` |
| `senologie-datenkranz` | Senologie-Datenkranz (DKG-zertifizierte Brustzentren) | breast | DE | `../SenologieOnFHIR` |
| `b1mg-cmd` | B1MG / EU Cancer Minimal Dataset | pan-cancer, minimal | EU | — |
| `nabon-mammacarcinoom` | NABON Informatiestandaard Mammacarcinoom | breast | NL | — |

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

## Provenance discipline

Each `sources/<key>/` folder should hold: the extracted `elements.csv` (the
spoke vocabulary), and a `SOURCE.md` recording exact version/date/URL of the
spec the elements were read from, so every mapping row is traceable.
