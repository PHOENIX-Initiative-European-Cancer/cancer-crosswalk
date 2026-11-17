#!/usr/bin/env python3
"""Build the ESMO breast-cancer *requirement* source and its hub mapping.

Input (curated below, derived from three traceable extractions kept under
sources/esmo-breast/ref/*-datapoints.md):
  - Loibl S et al. Early breast cancer: ESMO CPG. Ann Oncol 2024;35(2):159-182
  - de Azambuja E et al. Metastatic breast cancer: ESMO CPG. Ann Oncol 2026;37(9):1203-1219
  - Gennari A et al. ESMO CPG metastatic breast cancer. Ann Oncol 2021;32(12):1475-1495
    (superseded; used only where the 2026 main text defers detail to its supplement)

Every row is a DATA POINT a guideline recommendation depends on, consolidated
across the three texts (one row per concept, not per mention).

Output:
  sources/esmo-breast/elements.csv            one row per data point
  mappings/esmo-breast__to__eccdm.sssom.tsv   SSSOM rows for data points with a hub home
  docs/esmo-datapoints.md                     gap report: hub home, INT, four standards

Run:  python3 scripts/build_esmo_source.py
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HUB = REPO / "hub" / "eccdm" / "elements.csv"
OUT_ELEMENTS = REPO / "sources" / "esmo-breast" / "elements.csv"
OUT_MAPPING = REPO / "mappings" / "esmo-breast__to__eccdm.sssom.tsv"
OUT_DOC = REPO / "docs" / "esmo-datapoints.md"

STANDARDS = {
    "oBDS": "sources/mii-onko-obds/elements.csv",
    "NABON": "sources/nabon-mammacarcinoom/elements.csv",
    "B1MG": "sources/b1mg-cmd/elements.csv",
    "Senologie": "sources/senologie-datenkranz/elements.csv",
}
STANDARD_SETS = {
    "oBDS": "mappings/mii-onko-obds__to__eccdm.sssom.tsv",
    "NABON": "mappings/nabon-mammacarcinoom__to__eccdm.sssom.tsv",
    "B1MG": "mappings/b1mg-cmd__to__eccdm.sssom.tsv",
    "Senologie": "mappings/senologie-datenkranz__to__eccdm.sssom.tsv",
}
INT_ELEMENTS = "sources/int-breast/elements.csv"
INT_VALUES = "sources/int-breast/values.csv"

EBC = "EBC2024"
MBC = "MBC2026"
MBC21 = "MBC2021"

# carriage classes for data points WITHOUT a hub element (mirrors inverse_gaps)
BYREF = "by-reference"      # legacy label in the curated table; remapped in main() (see CODED / NEWMOD)
CODED = "coded-finding"     # terminology carries the meaning: generic coded finding by reference suffices
EXTEND = "extend-model"     # attribute of a model ECCDM already has
NEWMOD = "new-module"       # needs a new hub model
DERIVED = "derived"         # computable from hub elements (dates, sequences, composites)
PROCESS = "process"         # care-process / methodology item, not clinical content

# ---------------------------------------------------------------------------
# Curated table. Fields:
#   key, label, model, category, role, value_domain, decision, guidelines,
#   maps: list of (hub_element, predicate, confidence, comment)   (may be empty)
#   carriage: class when maps is empty (or the part a mapping does not cover)
#   probe: regex applied to the four standards' and INT's element lists
# ---------------------------------------------------------------------------
E = "skos:exactMatch"; C = "skos:closeMatch"; N = "skos:narrowMatch"; B = "skos:broadMatch"; R = "skos:relatedMatch"

ROWS: list[dict] = []


def row(key, label, model, category, role, value_domain, decision, guidelines,
        maps=(), carriage="", probe="", note=""):
    ROWS.append(dict(key=key, label=label, model=model, category=category, role=role,
                     value_domain=value_domain, decision=decision, guidelines=guidelines,
                     maps=list(maps), carriage=carriage, probe=probe, note=note))


PRED = "predictive"; PROG = "prognostic"; DIAG = "diagnostic"; REC = "treatment record"; MON = "monitoring"

# ----- Patient -----------------------------------------------------------
row("age", "Age at diagnosis", "Patient", "patient", PRED,
    "years; biological vs chronological age; ≥50 for APBI; DS-GPA component",
    "APBI eligibility, RT omission, geriatric assessment, DS-GPA; must not decide treatment alone", f"{EBC};{MBC}",
    [("CancerPatient.birthDate", R, 0.6, "Derivable from birthDate and the diagnosis date; the hub carries the date, not the age.")],
    probe=r"age_at|\balter\b|leeftijd|geburtsdat|birth_?(date|year)|birthdate")
row("sex", "Sex", "Patient", "patient", PRED, "female / male (male breast cancer)",
    "Tamoxifen rather than AI alone in men; GnRH agonist with CDK4/6i in men", f"{EBC};{MBC21}",
    [("CancerPatient.sexAtBirth", E, 0.9, "")], probe=r"geschlecht|\bsex|gender|geslacht")
row("menopausal_status", "Menopausal status", "Patient", "patient", PRED,
    "pre- / peri- / postmenopausal; serum estradiol and FSH if in doubt; treatment-induced amenorrhoea",
    "OFS mandatory with endocrine therapy in pre/perimenopausal; AI vs tamoxifen; bisphosphonate benefit", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"menopaus")
row("performance_status", "Performance status", "Patient", "patient", PRED,
    "ECOG/WHO scale (scale not fixed by ESMO); general health status",
    "ET alone instead of CDK4/6i combination; ChT decisions; treatment intensity", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"ecog|performance|leistungszustand|karnofsky|who.?status")
row("comorbidities", "Comorbidities", "Patient", "patient", PRED,
    "present/absent and type; cardiac disease; diabetes (HbA1c for alpelisib)",
    "ET alone vs CDK4/6i; single-agent ET when anti-HER2 unsafe; RT omission; alpelisib candidacy", f"{EBC};{MBC}",
    [("CancerPatient.comorbiditiesAtCancerDiagnosis", E, 0.9, "Hub fixes the time point at cancer diagnosis; the metastatic guideline needs comorbidities at MBC diagnosis, i.e. the same element re-asserted later.")],
    probe=r"comorb|komorb|nebendiagnose|charlson|\basa\b")
row("cardiac_function", "Cardiac function (LVEF)", "Patient", "patient", MON,
    "LVEF at baseline and during anthracycline / anti-HER2 therapy",
    "Cardiac monitoring; anti-HER2 or anthracycline eligibility", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"lvef|ejektion|ejection|echokard|herzfunktion|cardiac function")
row("geriatric_assessment", "Geriatric assessment / frailty", "Patient", "patient", PRED,
    "performed / result; biological age", "Treatment intensity in elderly patients", f"{EBC};{MBC21}",
    carriage=BYREF, probe=r"geriatr|\bg8\b|frailty|gebrechlich")
row("family_history", "Family history and hereditary risk category", "Patient", "patient", DIAG,
    "strong family history per national criteria; known high-risk pathogenic variant",
    "Screening pathway, breast MRI, germline testing", f"{EBC};{MBC21}",
    carriage=BYREF, probe=r"famil|erblich|heredit")
row("fertility", "Fertility wish, pregnancy and contraception", "Patient", "patient", PRED,
    "fertility wish; pregnancy status; fertility preservation performed; contraception counselled",
    "Fertility preservation before ChT; ET interruption for pregnancy; counselling in MBC", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"schwanger|pregnan|fertil|zwanger|contracep|kinderwunsch|verhütung")
row("body_measures", "Body weight / BMI", "Patient", "patient", MON,
    "weight, BMI", "Survivorship lifestyle counselling; dosing", EBC,
    carriage=BYREF, probe=r"\bbmi\b|gewicht|weight|körpergr|height|lengte")
row("lifestyle", "Lifestyle: physical activity, alcohol, smoking", "Patient", "patient", MON,
    "activity level; alcohol intake; smoking", "Survivorship counselling", EBC,
    carriage=BYREF, probe=r"rauch|smok|alkohol|alcohol|körperliche? aktivit|physical activity")
row("symptoms", "Symptoms (presenting, local, bone pain, neurological)", "Patient", "patient", DIAG,
    "symptomatic vs screen-detected; local symptoms of primary; bone pain severity; CNS symptoms",
    "Diagnostic imaging route; brain imaging only if symptomatic; LRT only if symptomatic; RT for painful bone lesions", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"symptom|beschwerde|klacht|schmerz|\bpain\b|wijze van detectie|screen")
row("patient_preference", "Patient preference / shared decision", "Patient", "other", PRED,
    "documented preference", "Every treatment recommendation; sequencing; surgery of primary", f"{EBC};{MBC}",
    carriage=PROCESS, probe=r"patientenwunsch|wens|preference|abweichung")

# ----- Diagnosis / pathology ---------------------------------------------
row("histology", "Histological type", "Pathology", "diagnosis/pathology", PROG,
    "WHO classification; lobular; special low-grade types (adenoid cystic, secretory, medullary); confirmed on metastatic biopsy",
    "MRI indication (lobular), APBI exclusion (lobular), ChT benefit in special types, confirmation of MBC", f"{EBC};{MBC}",
    [("CancerConditionAtDiagnosis.histologyBehaviour", E, 0.9, "ICD-O-3 morphology carries type and behaviour.")],
    probe=r"histolog|morpholog|icd-?o")
row("grade", "Histological grade", "Pathology", "diagnosis/pathology", PROG,
    "grade 1-3; DCIS nuclear grade", "ChT indication (HR+), abemaciclib/ribociclib eligibility, APBI, olaparib CPS+EG", f"{EBC}",
    [("CancerConditionAtDiagnosis.tumourGradeValue", E, 0.9, ""),
     ("CancerConditionAtDiagnosis.tumourGradeSystem", E, 0.85, "Grading system (Nottingham/Elston-Ellis) is implied, not named, by ESMO.")],
    probe=r"\bgrad(e|ing|o)?\b|graad")
row("tumour_size", "Tumour size (clinical and pathological, mm)", "Pathology", "diagnosis/pathology", PROG,
    "mm; thresholds 2 cm, 3 cm (APBI), 5 cm (abemaciclib, PMRT, staging imaging)",
    "Staging imaging trigger, APBI, PMRT, abemaciclib, neoadjuvant indication", EBC,
    carriage=BYREF, probe=r"tumou?r ?(size|gr[oö]sse)|tumorgr|grootte|diameter|\bsize\b",
    note="The hub carries the T category, not the measured size.")
row("laterality", "Laterality", "Pathology", "diagnosis/pathology", DIAG,
    "left / right / bilateral", "Bilateral imaging; contralateral surveillance", EBC,
    carriage=EXTEND, probe=r"lateral|seitenlok|\bseite\b|zijde|links|rechts",
    note="ECCDM bodySite is ICD-O topography without laterality; INT's workbook also asks for it (New Variables sheet).")
row("multifocality", "Multifocality / multicentricity", "Pathology", "diagnosis/pathology", PRED,
    "unifocal / multifocal / multicentric; number of lesions", "MRI indication, BCS feasibility, APBI exclusion", EBC,
    carriage=BYREF, probe=r"multifo|multizentr|multicentr|aantal (afwijkingen|laesies|haarden)")
row("lvi", "Lymphovascular invasion", "Pathology", "diagnosis/pathology", PROG,
    "present / absent", "APBI exclusion; PMRT intermediate risk", EBC,
    carriage=BYREF, probe=r"lymphovas|lymphgef|angioinvas|\bL[01]\b|\bV[01]\b|\blvi\b")
row("margins", "Resection margin status and width", "Pathology", "diagnosis/pathology", REC,
    "no tumour at ink (invasive); ≥2 mm (DCIS); ≥3 mm for low-risk DCIS APBI; involved margins",
    "Re-excision, boost, PMRT, APBI eligibility", EBC,
    carriage=BYREF, probe=r"margin|resektionsr|snijvlak|residualstatus|\bR[012]\b")
row("dcis", "DCIS component (presence, extent, grade, microinvasion)", "Pathology", "diagnosis/pathology", PROG,
    "pure DCIS vs invasive; size ≤2.5 cm; nuclear grade; microinvasion", "DCIS management; APBI; RT omission", EBC,
    carriage=BYREF, probe=r"dcis|in situ")
row("inflammatory", "Inflammatory breast cancer", "Pathology", "diagnosis/pathology", PRED,
    "yes / no (cT4d)", "ALND mandatory; no SLNB after PST; no immediate reconstruction", EBC,
    [("CancerStage.stage.value", N, 0.6, "Clinical diagnosis expressed as cT4d; a value of the T category rather than its own element.")],
    probe=r"inflammator|entzündlich")
row("nodal_pathology", "Axillary node pathology: nodes examined and positive, SLN details", "Pathology", "diagnosis/pathology", PROG,
    "number of SLNs removed / positive; macro- vs micrometastasis vs ITC; extracapsular extension; number of positive nodes (1-3, ≥4); residual axillary disease",
    "ALND vs axillary RT (Z0011/AMAROS criteria), PMRT, regional RT, abemaciclib and olaparib eligibility", EBC,
    carriage=BYREF, probe=r"sentinel|wächter|waechter|schildwacht|\bsln|lk_befallen|lk_untersucht|lymfeklieren|lymphknoten.*(befallen|untersucht|anzahl)|extrakapsul|extracapsul",
    note="The hub carries pN only; the counts and SLN detail that the ALN algorithm uses are pathology detail.")
row("pretreatment_node_biopsy", "Pretreatment axillary node histology / cytology", "Pathology", "diagnosis/pathology", DIAG,
    "performed / result; node marked (clip) before PST", "cN assignment; targeted axillary dissection after PST", EBC,
    carriage=BYREF, probe=r"(lymph|lk|lymfekl|axill).*(zytolog|cytolog|punctie|biops|feinnadel|fna)")
row("metastasis_biopsy", "Biopsy of a metastatic lesion at first MBC diagnosis", "Pathology", "diagnosis/pathology", DIAG,
    "performed / not feasible; site (avoid bone); re-biopsy at mixed response",
    "Confirms MBC; triggers receptor re-assessment", f"{MBC};{MBC21}",
    carriage=EXTEND, probe=r"biops.*(metast|recid|rezid)|metast.*biops",
    note="ClinicalCancerProgression has an assertedDate but no evidence/biopsy hook; CancerConditionAtDiagnosis.biopsyDate is the diagnosis only.")
row("subtype", "Biological subtype (luminal A/B-like, HER2-positive, triple-negative)", "Pathology", "diagnosis/pathology", PRED,
    "derived from ER, PgR, HER2, Ki-67 and grade; ER-low 1-9% behaves like TNBC",
    "Selects every systemic treatment algorithm; brain imaging strategy; DS-GPA", f"{EBC};{MBC}",
    carriage=DERIVED, probe=r"subtyp|luminal|triple|tripel|basal",
    note="Composite of the receptor and proliferation rows below.")

# ----- Biomarkers ---------------------------------------------------------
row("er", "Oestrogen receptor (ER) status", "Biomarker", "biomarker", PRED,
    "positive ≥1% cells; ER-low 1-9%; percentage; re-assessed on metastasis",
    "Endocrine therapy; subtype; PIK3CA testing; ET vs ChT", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"\b(er|oestrogen|estrogen|östrogen)\b|hormonrezeptor|hormoonrecept")
row("pgr", "Progesterone receptor (PgR) status", "Biomarker", "biomarker", PRED,
    "positive / negative; percentage", "HR status; subtype", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"\bpgr\b|\bpr\b.*(status|recept)|progest")
row("her2", "HER2 status (final category)", "Biomarker", "biomarker", PRED,
    "positive / negative; HER2-low (IHC 1+ or 2+/ISH-), HER2-ultralow, HER2-0; re-assessed on metastasis and in resected brain metastases",
    "Anti-HER2 therapy; T-DXd in HER2-low/ultralow; TNBC definition; gBRCA testing in HER2-negative", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"her2|her-2|her2neu")
row("her2_test", "HER2 test details (IHC score, ISH result)", "Biomarker", "biomarker", DIAG,
    "IHC 0 / 1+ / 2+ / 3+; ISH amplified / not; FISH/CISH mandatory at 2+",
    "Derives the HER2 category; ESCAT I-A only with ISH amplification", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"her2.*(ihc|ish|fish|score)|fish|cish|in situ hybrid")
row("ki67", "Ki-67 proliferation index", "Biomarker", "biomarker", PROG,
    "percentage; ≥20% high-risk (abemaciclib, ribociclib); luminal A vs B",
    "ChT indication, CDK4/6i eligibility, subtype", EBC,
    carriage=BYREF, probe=r"ki.?67|mib")
row("ki67_response", "Ki-67 after short preoperative endocrine therapy (endocrine response)", "Biomarker", "response", PRED,
    "Ki-67 ≤10% after 2-4 weeks of ET", "Estimates ChT benefit in HR+ with 0-3 nodes", EBC,
    carriage=BYREF, probe=r"ki.?67.*(response|verlauf|post|nach)|endokrine? ?(response|ansprech)")
row("gene_expression", "Multigene expression assay (Oncotype DX, MammaPrint, EndoPredict, Prosigna, BCI)", "Biomarker", "biomarker", PROG,
    "assay name; score; risk class", "ChT indication in HR+/HER2- with uncertain benefit", EBC,
    carriage=BYREF, probe=r"oncotype|mammaprint|genexpression|genprofiel|endopredict|prosigna|recurrence score|multigen")
row("tils", "Tumour-infiltrating lymphocytes (TILs)", "Biomarker", "biomarker", PROG,
    "percentage; no decision threshold", "Prognostic information in TNBC and HER2+", EBC,
    carriage=BYREF, probe=r"\btils?\b|tumou?r.?infiltrating|lymphozyt.*infiltr")
row("pdl1", "PD-L1 status, score type and assay", "Biomarker", "biomarker", PRED,
    "CPS ≥10 (22C3) for pembrolizumab; immune-cell ≥1% (SP142) for atezolizumab; not used in EBC",
    "ICI eligibility in metastatic TNBC; assay decides which regimen", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"pd-?l1")

# ----- Genetic ------------------------------------------------------------
row("gbrca", "Germline BRCA1/2 pathogenic variant", "Genetic", "genetic", PRED,
    "pathogenic / likely pathogenic / wild type; tested per national criteria or when olaparib candidate; all HER2-negative MBC",
    "Adjuvant olaparib; PARPi in MBC; carboplatin in TNBC; screening and MRI", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"brca|keimbahn|germline|kiemlijn|genmutatie|genetische_variante|erblich")
row("germline_other", "Other germline variants (PALB2, other high-risk genes)", "Genetic", "genetic", PRED,
    "PALB2 pathogenic / wild type; other high-risk PVs", "Olaparib/talazoparib (off-label) in MBC; screening pathway", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"palb2|chek2|\batm\b|\btp53\b|panel")
row("germline_testing", "Germline testing performed and genetic counselling", "Genetic", "genetic", REC,
    "offered / performed / counselled; date", "Prerequisite for the two rows above", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"genetik|genetisch|genetic (test|counsel)|humangenet|beratung")
row("pik3ca", "PIK3CA mutation (tissue or ctDNA)", "Genetic", "genetic", PRED,
    "mutated / wild type; exon 7, 9 or 20 for alpelisib", "Inavolisib triplet first line; capivasertib; alpelisib", MBC,
    carriage=BYREF, probe=r"pik3ca")
row("akt_pten", "AKT1 and PTEN alterations", "Genetic", "genetic", PRED,
    "altered / not", "Fulvestrant-capivasertib", MBC, carriage=BYREF, probe=r"akt1|pten")
row("esr1", "ESR1 mutation (ctDNA or tissue) after progression on AI", "Genetic", "genetic", PRED,
    "mutated / wild type; timing: at progression on AI ± CDK4/6i", "Elacestrant or imlunestrant", MBC,
    carriage=BYREF, probe=r"esr1")
row("somatic_brca", "Somatic BRCA1/2 mutation", "Genetic", "genetic", PRED,
    "pathogenic / likely pathogenic / wild type", "PARPi monotherapy", MBC, carriage=BYREF, probe=r"somatic.*brca|brca.*somat")
row("her2_mutation", "HER2 (ERBB2) mutation", "Genetic", "genetic", PRED,
    "mutated / not", "Neratinib-trastuzumab-fulvestrant, tucatinib or T-DXd in HER2-mutated MBC with brain metastases", MBC,
    carriage=BYREF, probe=r"erbb2|her2.*mutat")
row("tumour_agnostic", "Tumour-agnostic markers (NTRK fusion, MSI-H/dMMR, TMB)", "Genetic", "genetic", PRED,
    "present / absent", "Larotrectinib/entrectinib; pembrolizumab after subtype-specific options", MBC21,
    carriage=BYREF, probe=r"ntrk|\bmsi\b|dmmr|mismatch|\btmb\b|mutations?burden")
row("genomic_profiling", "Broader genomic profiling result with ESCAT tier and specimen type", "Genetic", "genetic", PRED,
    "actionable alteration list; ESCAT I-A to II-B; specimen = ctDNA / metastatic tissue / primary tissue; test date",
    "Treatment change or trial access only if ESCAT-actionable; which material supports ESR1 and PI3K-pathway calls", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"ctdna|liquid|ngs|sequenc|panel|molekular|molecul|somatische")
row("pharmacogenetics", "Pharmacogenetic tests (DPD/DPYD before capecitabine, UGT1A1)", "Genetic", "genetic", PRED,
    "deficient / normal", "Capecitabine initiation; sacituzumab toxicity risk", f"{MBC};{MBC21}",
    carriage=BYREF, probe=r"\bdpd\b|dpyd|ugt1a1|pharmakogen")

# ----- Staging ------------------------------------------------------------
row("ctnm", "Clinical TNM categories (cT, cN, cM) per UICC TNM8", "Staging", "staging", PROG,
    "cT0-4 (incl. T4d), cN0-3, cM0/1; cN2-3 bulky; T1c/N0 or greater triggers neoadjuvant ChT in TNBC",
    "Staging imaging triggers, neoadjuvant indication, SLNB vs ALND, abemaciclib/ribociclib/olaparib eligibility", f"{EBC}",
    [("CancerStage.stage.value", N, 0.85, "Each category is one stage block with code = T/N/M and type = clinical."),
     ("CancerStage.stage.code", N, 0.85, ""),
     ("CancerStage.type", N, 0.8, "type = clinical")],
    probe=r"\bctnm\b|\bc[tn]\s?[0-4x]|klinisch.*(tnm|stadium)|\bc[TN]-?(stadium|categorie|kategorie)|tnm.*(klinisch|clinical|\bc\b)")
row("ptnm", "Pathological TNM categories (pT, pN, pM)", "Staging", "staging", PROG,
    "pT1a/b/c-pT4, pN0(i+)/pN1mi/pN1-3; pT1 pN0 de-intensified anti-HER2; ≥pT2 or ≥pN1 olaparib in TNBC",
    "Adjuvant regimen intensity, PMRT, nodal RT, olaparib", EBC,
    [("CancerStage.stage.value", N, 0.85, "type = pathological"), ("CancerStage.stage.code", N, 0.85, ""), ("CancerStage.type", N, 0.8, "")],
    probe=r"\bptnm\b|\bp[tn]\s?[0-4x]|patholog.*(tnm|stadium)|\bp[TN]-?(stadium|categorie|kategorie)|tnm.*(patholog|\bp\b)")
row("yptnm", "Post-neoadjuvant pathological and clinical categories (ypT, ypN, ycN)", "Staging", "staging", PROG,
    "ypT0/is ypN0 = pCR; ypN1mi or ypN+ -> ALND; ycN0 after cN1 -> SLNB/TAD",
    "ALND after PST, post-neoadjuvant systemic therapy (T-DM1, capecitabine, olaparib, pembrolizumab)", EBC,
    [("CancerStage.stage.value", N, 0.8, "Needs a stage type value for post-therapy (y) staging; ECCDM type binding lists clinical and pathological only."),
     ("CancerStage.type", N, 0.6, "y-prefix (post-therapy) is not a distinct ECCDM stage type.")],
    probe=r"\byp[tn]\b|\byc[n]\b|post.?neoadj|nach neoadj")
row("stage_group", "Stage group (UICC/AJCC 8th)", "Staging", "staging", PROG,
    "stage I-IV; IIb or higher triggers distant staging; stage II-III -> neoadjuvant", "Staging imaging, neoadjuvant indication, ribociclib (stage II-III)", EBC,
    [("CancerStage.stage.value", N, 0.8, "Stage group as a stage block with code = stage group."), ("CancerStage.stage.code", N, 0.8, "")],
    probe=r"stadium|stage group|uicc|ajcc|stadia")
row("staging_system", "Staging system and edition", "Staging", "staging", REC, "UICC TNM 8th edition; WHO classification",
    "Comparability of stage", f"{EBC}", [("CancerStage.classificationType", E, 0.9, "")], probe=r"tnm.?version|edition|auflage|classificat")
row("cpseg", "CPS+EG score", "Staging", "staging", PRED,
    "score from pretreatment clinical stage, post-treatment pathological stage, ER and grade; ≥3 for olaparib in HR+ non-pCR",
    "Olaparib eligibility in HR+ residual disease", EBC, carriage=DERIVED, probe=r"cps\+?eg|cps.?eg",
    note="Composite of cTNM, ypTNM, ER and grade rows.")
row("risk_composites", "Composite risk categories (monarchE, NATALEE, OlympiA definitions)", "Staging", "staging", PRED,
    "≥4 nodes, or 1-3 nodes with T3 / grade 3 / Ki-67 ≥20%; stage II (N0 with G2-3 or Ki-67 ≥20%, or N1) or III",
    "Abemaciclib, ribociclib, olaparib eligibility", EBC, carriage=DERIVED, probe=r"risikogruppe|risk (group|categor)|hochrisiko",
    note="Composite of nodal, size, grade and Ki-67 rows.")
row("metastatic_sites", "Metastatic sites and extent", "Staging", "staging", PROG,
    "sites (bone, liver, lung, brain, leptomeninges); visceral vs non-visceral; number of lesions; oligometastatic (≤5 lesions, all treatable)",
    "Monitoring interval, OMD multimodality approach, surgery of primary, site-specific management", f"{MBC};{MBC21}",
    [("ClinicalCancerProgression.metastaticSites", E, 0.9, ""),
     ("ClinicalCancerProgression.extentType", R, 0.5, "Oligo- vs polymetastatic is a count, not an extent type.")],
    probe=r"fernmetast|metastas.*(lokal|locat|site)|menge_fm|metastaticsite")
row("bone_pattern", "Bone-only / bone-predominant disease", "Staging", "staging", PRED,
    "yes / no", "Repeat bone scans; surgery of primary consideration", f"{MBC};{MBC21}",
    [("ClinicalCancerProgression.metastaticSites", R, 0.6, "Derivable from the set of metastatic sites.")], carriage=DERIVED,
    probe=r"knochenmet|bone.?only|ossär|botmet")
row("brain_mets", "Brain metastases: presence, activity, number, neurological symptoms", "Staging", "staging", PRED,
    "present / absent; active vs stable; count; symptomatic", "T-DXd, tucatinib triplet, SRT vs WBRT, DS-GPA, continuation of systemic therapy", f"{MBC};{MBC21}",
    [("ClinicalCancerProgression.metastaticSites", N, 0.7, "Site = brain; activity status and lesion count are not carried.")],
    probe=r"hirnmet|brain met|cerebr|hersen|zns|cns")
row("leptomeningeal", "Leptomeningeal disease (type I/II, nodular vs linear, CSF cytology)", "Staging", "staging", PRED,
    "suspected / confirmed; type I (positive cytology or biopsy) / II; morphology", "Lumbar puncture; intrathecal therapy only in type I; RT field", MBC,
    [("ClinicalCancerProgression.metastaticSites", N, 0.6, "Site = leptomeninges; type and cytology are not carried.")],
    probe=r"leptomening|meningeosis|liquor|csf")
row("bone_complications", "Bone lesion complications: fracture risk, SINS, spinal cord compression", "Staging", "staging", PRED,
    "impending fracture (CT/X-ray); SINS; MSCC suspected/confirmed; complicated vs uncomplicated lesion; significant long-bone/vertebral lesions",
    "RT dose (8 Gy x1 vs fractionated), orthopaedic evaluation, stabilisation surgery, MRI", f"{MBC};{MBC21}",
    carriage=BYREF, probe=r"fraktur|fracture|sins\b|spinal|rückenmark|myelokompr|cord compression")
row("disease_tempo", "Disease tempo: visceral crisis / imminent organ failure, aggressiveness", "Staging", "staging", PRED,
    "present / absent; indolent vs aggressive; need for rapid response",
    "ChT instead of ET-based therapy; combination vs sequential ChT; monitoring interval", f"{MBC};{MBC21}",
    carriage=BYREF, probe=r"visceral|viszeral|organ failure|organversagen|krise|crisis")
row("de_novo", "De novo vs recurrent metastatic disease; intact primary", "Staging", "staging", PRED,
    "de novo stage IV / recurrent; primary intact or resected", "AI-CDK4/6i first line; MDT for stage IV with intact primary; LRT of primary", f"{MBC};{MBC21}",
    [("CancerStage.stage.value", R, 0.6, "cM1 at diagnosis = de novo; otherwise recurrence is a ClinicalCancerProgression event."),
     ("ClinicalCancerProgression.diseaseStatus", R, 0.6, "")], carriage=DERIVED,
    probe=r"de.?novo|primär metast|falltyp|ersterkrank|rezidiv|recidief|recurren")
row("dfi", "Disease-free interval and treatment-free interval", "Staging", "staging", PRED,
    "months from end of (neo)adjuvant therapy to relapse; thresholds <6, ≥6, ≥12 months; ≥12 months after CDK4/6i",
    "ICI eligibility (≥6 / ≥12), ADC choice (<6), anthracycline/taxane rechallenge (≥12), CDK4/6i rechallenge", f"{MBC};{MBC21}",
    [("ClinicalCancerProgression.assertedDate", R, 0.6, "Derivable: progression date minus SystemicTreatment.endDate of the last adjuvant agent."),
     ("SystemicTreatment.endDate", R, 0.6, "")], carriage=DERIVED,
    probe=r"disease.?free|rezidivfrei|krankheitsfrei|interval|dfi\b")
row("endocrine_resistance", "Timing of relapse relative to adjuvant endocrine / anti-HER2 therapy (endocrine resistance class)", "Staging", "staging", PRED,
    "on adjuvant ET, ≤12 months after, >12 months after; within 24 months of adjuvant ET; within 6-12 months of adjuvant pertuzumab/T-DM1; primary vs secondary endocrine resistance; PFS on prior ET",
    "AI vs fulvestrant backbone, CDK4/6i partner, T-DXd after one ET line, second-line options used first line", f"{MBC};{MBC21}",
    [("ClinicalCancerProgression.assertedDate", R, 0.6, "Derivable from progression date and the end date / type of the adjuvant systemic treatment."),
     ("SystemicTreatment.endDate", R, 0.6, ""), ("SystemicTreatment.type", R, 0.5, "")], carriage=DERIVED,
    probe=r"endokrine? ?(resist|sensit)|endocrine.?(resist|sensit)|hormoonresist")
row("labs", "Baseline laboratory values and organ function", "Staging", "other", DIAG,
    "full blood count, liver and renal function, alkaline phosphatase, calcium; HbA1c (alpelisib); organ function adequate / impaired",
    "Minimum work-up before surgery and systemic therapy; second-line selection; alpelisib eligibility", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"hba1c|blutbild|blood count|leberwert|liver function|kreatinin|creatinin|renal|calcium|alkalische|labor(wert|befund)")

# ----- Imaging ------------------------------------------------------------
row("breast_imaging", "Diagnostic breast imaging performed (mammography, ultrasound, tomosynthesis, CEM, MRI)", "Imaging", "imaging", DIAG,
    "modality; bilateral; regional nodes; MRI indications (uncertainty, gBRCA, lobular, multifocality, implants); baseline MRI before PST",
    "Diagnostic work-up; extent of residual disease after PST", EBC,
    [("Imaging.type", E, 0.9, ""), ("Imaging.bodySite", E, 0.85, "")],
    probe=r"mammograph|sonograph|ultrasound|echo|\bmrt\b|\bmri\b|tomosynth|bildgebung|beeldvorm")
row("imaging_findings", "Imaging findings (BI-RADS, lesion extent, residual disease, radiation necrosis)", "Imaging", "imaging", DIAG,
    "BI-RADS; size/extent; residual disease after PST; necrosis vs progression on brain imaging",
    "Biopsy indication, surgical planning after PST, bevacizumab for radiation necrosis", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"bi-?rads|herdbefund|bevinding|mikrokalk|calcificat|residual.*(imaging|bildgeb)|acr.?dichte")
row("staging_imaging", "Staging imaging performed (chest CT, abdominal US/CT/MRI, bone scintigraphy, FDG-PET-CT)", "Imaging", "imaging", DIAG,
    "modality; indicated for stage IIb+, cN+, T ≥5 cm, aggressive biology, symptoms; minimum MBC baseline = CT chest/abdomen + bone scan; PET-CT alternative",
    "Distant staging; baseline for monitoring", f"{EBC};{MBC}",
    [("Imaging.type", E, 0.9, ""), ("Imaging.bodySite", E, 0.85, "")],
    probe=r"computertomo|ct-?scan|ct (thorax|abdomen|chest)|skelettszinti|bone scan|knochenszinti|szintigra|scintigra|\bpet\b|pet-?ct|botscan")
row("cns_bone_imaging", "CNS and bone-specific imaging (brain MRI, spine MRI, CT/X-ray for fracture risk)", "Imaging", "imaging", DIAG,
    "performed / modality; brain imaging only if symptomatic or subtype-oriented", "Brain metastasis detection, MSCC, fracture risk", f"{MBC};{MBC21}",
    [("Imaging.type", N, 0.8, "Specific imaging types; the trigger (symptoms, subtype) is in the symptoms row.")],
    probe=r"schädel|cranial|brain mri|hirn.*(mrt|ct)|wirbelsäule|spine")
row("imaging_dates", "Imaging dates and interval to treatment start; modality consistency", "Imaging", "imaging", MON,
    "date; ≤4 weeks between baseline imaging and treatment start; same modality at baseline and monitoring; every 2-4 months",
    "Timeliness of staging; comparability of response assessment", f"{EBC};{MBC}",
    [("CancerConditionAtDiagnosis.imagingDate", C, 0.7, "Only the diagnosis imaging date exists; ECCDM Imaging has no date of its own.")],
    carriage=EXTEND, probe=r"(datum|date).*(bildgeb|imaging|untersuch)|untersuchungsdatum|onderzoeksdatum")

# ----- Surgery ------------------------------------------------------------
row("surgery_event", "Surgery performed: date, body site, intent, setting relative to systemic therapy", "Surgery", "surgery", REC,
    "date; breast / axilla / metastasis; curative vs palliative; after PST or primary",
    "Sequencing; adjuvant start interval; post-PST surgical planning", f"{EBC};{MBC}",
    [("Surgery.date", E, 0.95, ""), ("Surgery.bodySite", E, 0.9, ""), ("Surgery.intent", E, 0.85, "")],
    probe=r"op.?datum|operation.*datum|surgery date|datum operatie|op_datum")
row("breast_surgery_type", "Breast surgery type (BCS, mastectomy and its variants, oncoplastic)", "Surgery", "surgery", REC,
    "BCS; mastectomy; nipple-sparing; skin-sparing; oncoplastic; surgical removal of primary in stage IV",
    "RT indication (WBRT vs PMRT), reconstruction, local control", f"{EBC};{MBC}",
    carriage=EXTEND, probe=r"art_eingriff|operation\.art|\bops\b|type operatie|mastect|brusterhalt|\bbcs\b|operatie tumor",
    note="ECCDM Surgery has intent, date and bodySite but no procedure type; the INT code list shows the same gap.")
row("axillary_surgery", "Axillary surgery type (SLNB, targeted axillary dissection, ALND)", "Surgery", "surgery", REC,
    "SLNB; TAD with clipped node and ≥3 SLNs, dual tracer; ALND; none", "Axillary RT vs ALND, regional RT extent", EBC,
    carriage=EXTEND, probe=r"sentinel|axill|alnd|okselkl|lymphadenektomie")
row("reconstruction", "Breast reconstruction (timing, technique, implant)", "Surgery", "surgery", REC,
    "immediate / delayed; autologous / implant; implant type", "PMRT sequencing; RT tolerance", EBC,
    carriage=EXTEND, probe=r"rekonstruk|reconstruct|implantat|prothese")
row("surgical_marking", "Surgical marking (tumour bed clips, primary site marker before PST, clipped positive node)", "Surgery", "surgery", REC,
    "placed / retrieved", "Boost planning, APBI, targeted axillary dissection", EBC,
    carriage=EXTEND, probe=r"\bclip|markierung|drahtmark|(?<!bio)marker\b|tumou?r bed")
row("local_therapy_metastases", "Local therapy of metastases (ablation, SIRT, stabilisation surgery) and oophorectomy", "Surgery", "surgery", REC,
    "image-guided ablation; surgery; orthopaedic stabilisation / separation surgery; bilateral oophorectomy",
    "OMD multimodality treatment; MSCC; rapid oestrogen suppression", f"{MBC};{MBC21}",
    [("Surgery.date", E, 0.8, ""), ("Surgery.bodySite", E, 0.8, ""), ("Surgery.intent", C, 0.7, "Palliative / local-control intent; procedure type itself is not carried.")],
    probe=r"ablation|radiofrequen|sirt|stabilis|ovarektomie|oophorect|adnexekt")

# ----- Radiotherapy -------------------------------------------------------
row("rt_target", "Radiotherapy target (whole breast, partial breast, chest wall, regional nodes incl. levels and IMN, brain, bone)", "Radiotherapy", "radiotherapy", REC,
    "target volume; nodal levels 1-4; internal mammary nodes; CT-planned per ESTRO", "Locoregional control; regional RT after positive SLNB without ALND", f"{EBC};{MBC}",
    [("Radiotherapy.bodySite", E, 0.9, "Nodal level detail is finer than a body-site code.")],
    probe=r"zielvolumen|target volume|bestrahlungs.*(ort|region|ziel)|locatie radioth|st\.zielgebiet|rt_site")
row("rt_dates_intent", "Radiotherapy dates, intent and setting", "Radiotherapy", "radiotherapy", REC,
    "start / end; adjuvant vs palliative; after BCS / after mastectomy / after reconstruction; concurrent with T-DM1 or ET",
    "Sequencing with systemic therapy and reconstruction", f"{EBC};{MBC}",
    [("Radiotherapy.startDate", E, 0.95, ""), ("Radiotherapy.endDate", E, 0.95, ""), ("Radiotherapy.intent", E, 0.85, ""), ("Radiotherapy.setting", E, 0.8, "")],
    probe=r"strahlenth.*(beginn|ende|datum)|radioth.*(start|end|datum)|st\.(beginn|ende)")
row("rt_boost", "Tumour bed boost", "Radiotherapy", "radiotherapy", REC, "given / not; dose 10-16 Gy",
    "Local recurrence reduction in unfavourable risk", EBC, carriage=EXTEND, probe=r"boost")
row("rt_dose", "Radiotherapy dose and fractionation", "Radiotherapy", "radiotherapy", REC,
    "total dose; fractions; conventional / moderate hypofractionation (15-16 fx) / ultra-hypofractionation (26 Gy/5 fx); 8 Gy x1 bone; weekly 5.7-6 Gy for frail",
    "Regimen choice; bone metastasis RT", f"{EBC};{MBC}", carriage=EXTEND, probe=r"dosis|\bdose\b|fraktion|fractie|\bgy\b|gesamtdosis")
row("rt_technique", "Radiotherapy technique (APBI type, SRT vs whole-brain, brachytherapy, intraoperative)", "Radiotherapy", "radiotherapy", REC,
    "external beam / brachytherapy / intraoperative; stereotactic vs WBRT; involved-field for LMD",
    "APBI delivery; SRT preferred over WBRT; avoid SRT concurrent with ADC", f"{EBC};{MBC}",
    carriage=EXTEND, probe=r"bestrahlungstechnik|rt.?techni|radiotherapy technique|stereotak|stereotac|apbi|teilbrust|brachy|intraoperativ")

# ----- Systemic treatment -------------------------------------------------
row("systemic_class", "Systemic therapy class", "SystemicTreatment", "systemic therapy", REC,
    "endocrine (AI, tamoxifen, fulvestrant, oral SERD), OFS, chemotherapy, anti-HER2, CDK4/6i, PI3K/AKT pathway inhibitor, PARPi, ICI, ADC, bone-modifying agent, anti-angiogenic, everolimus, tumour-agnostic",
    "Every algorithm branch; 'at least two ET lines before ChT'", f"{EBC};{MBC}",
    [("SystemicTreatment.type", E, 0.9, "ECCDM type is the therapy category; INT reports immunotherapy missing in its registry.")],
    probe=r"systemische therap|systemic (therapy|treatment)|therapieart|chemotherap|hormontherap|endokrine therap|antihormon|immuntherap|antikörpertherap|targeted therap|zielgerichtet|systemische behandel")
row("systemic_agent", "Systemic agent and regimen (substance level)", "SystemicTreatment", "systemic therapy", REC,
    "named agent (e.g. abemaciclib, ribociclib, olaparib, pembrolizumab, trastuzumab, pertuzumab, T-DM1, T-DXd, tucatinib, sacituzumab govitecan, Dato-DXd, capivasertib, alpelisib, inavolisib, elacestrant, capecitabine, carboplatin, denosumab); regimen (AC/EC-taxane, dose-dense with G-CSF, docetaxel ≥6 cycles)",
    "'If not already used' rules; maintenance after induction; rechallenge; sequencing of ADCs and TKIs", f"{EBC};{MBC}",
    [("SystemicTreatment.type", N, 0.7, "Substance is narrower than the ECCDM therapy category; the sequencing rules in MBC need the agent.")],
    carriage=EXTEND, probe=r"substanz|wirkstoff|medicatie|medikament|agent|regime|protokoll|\batc\b|schema")
row("systemic_dates", "Systemic therapy start and end dates, ongoing flag", "SystemicTreatment", "systemic therapy", REC,
    "dates; ongoing; neoadjuvant start within 2-4 weeks of staging; adjuvant start within 4-6 weeks of surgery (not >12)",
    "Timeliness; DFI; line counting", f"{EBC};{MBC}",
    [("SystemicTreatment.startDate", E, 0.95, ""), ("SystemicTreatment.endDate", E, 0.95, ""), ("SystemicTreatment.ongoing", E, 0.9, "")],
    probe=r"(therapie|behandel|treatment).*(beginn|start|ende|end).*(datum|date)?|syst\.(beginn|ende)")
row("systemic_setting", "Treatment setting and line of therapy", "SystemicTreatment", "systemic therapy", REC,
    "neoadjuvant / adjuvant / post-neoadjuvant / extended adjuvant / metastatic line 1, 2, 3+; number of prior ET and ChT lines in MBC",
    "Post-neoadjuvant therapy selection; T-DXd after ≥2 ET lines; SG/Dato-DXd after ≥1 ChT line; monitoring frequency", f"{EBC};{MBC}",
    [("SystemicTreatment.setting", E, 0.85, "Setting values cover neoadjuvant/adjuvant; the metastatic line number needs a value or a count derived from the sequence (NABON precedent: Behandellijn -> setting, closeMatch).")],
    probe=r"stellung_op|stellung zur op|\bsetting\b|neoadjuv|\badjuvant|behandellijn|therapielinie|line of (therapy|treatment)")
row("systemic_intent", "Systemic therapy intent", "SystemicTreatment", "systemic therapy", REC, "curative / palliative; maintenance",
    "Framing of every MBC decision (incurable disease)", f"{EBC};{MBC}",
    [("SystemicTreatment.intent", E, 0.9, "")], probe=r"intention|intent|therapieziel|treatment aim")
row("systemic_delivery", "Treatment delivery: cycles, duration, dose reduction, delay, stop reason", "SystemicTreatment", "systemic therapy", REC,
    "cycles given (docetaxel ≥6); duration (ET 5-10 years, abemaciclib 2 years, ribociclib 3 years, anti-HER2 12 months, BMA 2 years); dose reduction; delay; stop reason (PD, toxicity, cumulative dose, choice); cumulative anthracycline dose",
    "Maintenance switch, toxicity management, rechallenge feasibility", f"{EBC};{MBC}",
    carriage=EXTEND, probe=r"zyklen|cycles|dosisreduktion|dose reduction|abbruch|discontinu|ende_grund|stop|unterbrech|kumulativ")
row("ofs", "Ovarian function suppression / ablation", "SystemicTreatment", "systemic therapy", REC,
    "GnRH agonist / bilateral oophorectomy / none", "Required with ET in pre/perimenopausal women; premenopausal treated as postmenopausal only with OFS", f"{EBC};{MBC}",
    [("SystemicTreatment.type", N, 0.7, "A subtype of endocrine therapy.")], probe=r"ovar.*(suppress|ablat)|gnrh|lhrh|\bofs\b")
row("bma", "Bone-modifying agent (agent, schedule, duration) and dental evaluation", "SystemicTreatment", "systemic therapy", REC,
    "denosumab q4w; zoledronic acid q4w -> q12w after ≥9 months stable; adjuvant bisphosphonate; interruption after 2 years in remission; dental evaluation and calcium/vitamin D before start",
    "SRE prevention; adjuvant recurrence reduction; de-escalation", f"{EBC};{MBC}",
    [("SystemicTreatment.type", N, 0.7, "Schedule, duration and the dental prerequisite are not carried.")],
    probe=r"bisphosph|denosumab|zoledron|antiresorpt|knochenschutz|bone.?modif")
row("prior_exposure", "Prior exposure per agent class and setting ('not already used')", "SystemicTreatment", "systemic therapy", REC,
    "prior AI, CDK4/6i, taxane-trastuzumab, T-DXd, T-DM1, tucatinib, TKI, PARPi, ICI, sacituzumab, Dato-DXd, anthracycline, taxane; agents received in (neo)adjuvant vs metastatic setting",
    "Eligibility of nearly every MBC regimen; continuation with agents not previously received", f"{MBC};{MBC21}",
    [("SystemicTreatment.type", R, 0.5, "Derivable from the patient's SystemicTreatment history only if the agent (not just the class) is recorded.")],
    carriage=DERIVED, probe=r"vortherap|prior (therap|treatment|exposure)|voorbehandel|previous treatment")
row("prior_response", "Response and duration on prior therapy (PFS on prior ET, duration of CDK4/6i response, progression on taxane-trastuzumab)", "SystemicTreatment", "response", PRED,
    "months; prolonged vs short; progression during vs after; endocrine-sensitive / resistant / refractory",
    "Second-line endocrine vs non-endocrine; oral SERD preference; T-DXd / tucatinib after taxane-trastuzumab", f"{MBC};{MBC21}",
    [("ClinicalCancerProgression.assertedDate", R, 0.6, "Derivable from progression dates and the dates of the preceding SystemicTreatment."),
     ("OverallCancerTreatmentResponse.treatmentResponseType", R, 0.5, "")], carriage=DERIVED,
    probe=r"ansprech.*(dauer|vorther)|response.*(duration|prior)|pfs|progressionsfrei")
row("contraindications", "Contraindications and candidacy (ChT, anthracycline, taxane, ET, tamoxifen in men, ICI, everolimus)", "SystemicTreatment", "systemic therapy", PRED,
    "contraindicated / not; candidate / not; immune-toxicity risk factors",
    "Non-anthracycline regimens; ET + anti-HER2 without ChT; less toxic ChT partner; non-ICI first line", f"{EBC};{MBC}",
    carriage=BYREF, probe=r"kontraindik|contraindic|contra-indicatie|unverträglich|intoleran")
row("supportive_medication", "Supportive co-medication (G-CSF, steroid mouthwash, calcium/vitamin D, premedication, stomatitis prophylaxis)", "SystemicTreatment", "systemic therapy", REC,
    "given / not; duration", "Dose-dense ChT; everolimus; BMA; paclitaxel premedication", f"{EBC};{MBC}",
    carriage=EXTEND, probe=r"g-?csf|supportiv|begleitmedikation|premedic|prophyla")
row("treatment_timing", "Intervals between diagnosis, surgery and systemic therapy start", "SystemicTreatment", "systemic therapy", MON,
    "diagnosis/staging -> neoadjuvant start 2-4 weeks; surgery -> adjuvant start 4-6 weeks, efficacy loss >12 weeks; imaging -> MBC treatment ≤4 weeks",
    "Quality of care; timeliness", f"{EBC};{MBC}",
    [("SystemicTreatment.startDate", R, 0.6, "Derivable from startDate with Surgery.date / CancerConditionAtDiagnosis dates."),
     ("Surgery.date", R, 0.6, "")], carriage=DERIVED, probe=r"wartezeit|interval|zeit bis|time to treatment")

# ----- Response -----------------------------------------------------------
row("pcr", "Pathological response after neoadjuvant therapy (pCR, residual disease, RCB)", "Response", "response", PROG,
    "pCR = ypT0/is ypN0; residual invasive disease in breast or nodes; micrometastases after PST = non-pCR; HER2 status of residual specimen",
    "T-DM1 vs trastuzumab, capecitabine, olaparib, pembrolizumab continuation; prognosis", EBC,
    [("OverallCancerTreatmentResponse.treatmentResponseType", N, 0.8, "Pathological response is one response assessment type (NABON precedent: PA-respons -> closeMatch).")],
    probe=r"\bpcr\b|pathologic.*(complete|response|respons)|regression|residual cancer burden|\brcb\b|regressie|remission")
row("clinical_response", "Clinical / imaging response category and date", "Response", "response", MON,
    "CR / PR / SD / PD / mixed; every 2-4 months in MBC; initial response in OMD; clinical/imaging response to PST",
    "Next line; LRT timing in OMD; surgical planning after PST; BMA de-escalation on stable disease", f"{EBC};{MBC}",
    [("OverallCancerTreatmentResponse.treatmentResponseType", E, 0.85, ""), ("OverallCancerTreatmentResponse.date", E, 0.9, "")],
    probe=r"ansprech|respons|remission|recist|gesamtbeurteilung")
row("progression_event", "Progression event: date, status, sites (intracranial vs extracranial)", "Response", "response", MON,
    "date; progression / stable; CNS-only vs extracranial; suspected progression triggers tests",
    "Triggers next line; CNS-only progression keeps systemic therapy; continuation after SRT", f"{MBC};{MBC21}",
    [("ClinicalCancerProgression.assertedDate", E, 0.9, ""), ("ClinicalCancerProgression.diseaseStatus", E, 0.9, ""),
     ("ClinicalCancerProgression.metastaticSites", E, 0.85, ""), ("ClinicalCancerProgression.locoRegionalSites", E, 0.8, "")],
    probe=r"progress|verlauf|tumorstatus|recidief|rezidiv")
row("remission_status", "Remission / stable-disease status under long-term therapy", "Response", "response", PRED,
    "stable ≥9 months (zoledronic acid q12w); in remission (BMA interruption after 2 years)", "BMA de-escalation and interruption", MBC,
    [("OverallCancerTreatmentResponse.treatmentResponseType", R, 0.6, "Derivable from the response record over time.")], carriage=DERIVED,
    probe=r"remission|stable disease|stabil")

# ----- Follow-up / survivorship -------------------------------------------
row("followup_visit", "Follow-up visit: date, vital status, evidence of disease", "FollowUp", "follow-up", MON,
    "visits every 3-4 months (years 1-2), 6 months (3-5), yearly; vital status; disease evidence",
    "Recurrence detection; survivorship", EBC,
    [("LastFollowUp.date", E, 0.95, ""), ("LastFollowUp.vitalStatus", E, 0.9, ""), ("LastFollowUp.evidenceOfDisease", E, 0.9, "")],
    probe=r"nachsorge|follow.?up|verlauf|controle|vitalstatus")
row("recurrence", "Recurrence (local, regional, distant)", "FollowUp", "follow-up", MON,
    "local / regional / distant; date; sites", "Aims of follow-up; defines MBC", f"{EBC};{MBC}",
    [("ClinicalCancerProgression.diseaseStatus", E, 0.9, ""), ("ClinicalCancerProgression.locoRegionalSites", E, 0.85, ""),
     ("ClinicalCancerProgression.metastaticSites", E, 0.85, "")],
    probe=r"rezidiv|recidief|recurren|lokalrezidiv")
row("second_primary", "Contralateral breast cancer and second primary cancers", "FollowUp", "follow-up", MON,
    "contralateral BC; second primary; participation in other-cancer screening", "Aims of follow-up; annual bilateral mammography", EBC,
    [("CancerConditionAtDiagnosis.bodySite", R, 0.5, "A new CancerConditionAtDiagnosis instance, linked to the same patient; ECCDM has no second-tumour link.")],
    carriage=EXTEND, probe=r"zweittumor|second primary|kontralateral|contralateral|tweede tumor")
row("surveillance_imaging", "Surveillance imaging (annual mammography, breast US/MRI)", "FollowUp", "imaging", MON,
    "annual ipsilateral (after BCS) and contralateral mammography; US/MRI in selected cases; no routine CT/bone scan/tumour markers in asymptomatic patients",
    "Follow-up schedule", EBC, [("Imaging.type", E, 0.8, "ECCDM Imaging has no date or purpose, so surveillance is not distinguishable from diagnosis imaging.")],
    probe=r"nachsorge.*(mammo|bildgeb)|surveillance|screening.*(follow|nachsorge)")
row("adverse_events", "Treatment toxicity and adverse events (type, CTCAE grade, immune-related, cardiotoxicity, surgical complications)", "FollowUp", "follow-up", MON,
    "event, grade, causal therapy, date; assessed at each visit; remaining toxicities from prior therapy",
    "Dose reduction / delay; rechallenge only without remaining toxicity; supportive care", f"{EBC};{MBC}",
    carriage=NEWMOD, probe=r"toxi|nebenwirk|adverse|ctcae|bijwerking|komplik|complicat")
row("skeletal_events", "Skeletal-related events", "FollowUp", "follow-up", MON,
    "fracture, MSCC, RT or surgery to bone, hypercalcaemia; first / subsequent; date", "Outcome that BMA therapy targets", f"{MBC};{MBC21}",
    carriage=BYREF, probe=r"skeletal.?related|\bsre\b|skelettbezogen|pathologische fraktur")
row("bone_density", "Bone mineral density", "FollowUp", "follow-up", MON,
    "DXA result; osteopenia / osteoporosis under AI or OFS", "Bisphosphonate indication; survivorship", EBC,
    carriage=BYREF, probe=r"knochendichte|bone density|\bdxa\b|osteopor|botdichtheid")
row("pro_qol", "Patient-reported outcomes, quality of life, psychosocial and sexual health", "FollowUp", "follow-up", MON,
    "ePRO instrument scores at each visit; QoL in efficacy evaluation; anxiety, depression, fatigue, sleep, cognition, work; sexual and genitourinary symptoms; palliative symptom burden",
    "Toxicity detection; supportive and palliative care; shared decisions", f"{EBC};{MBC}",
    carriage=NEWMOD, probe=r"\bqol\b|quality of life|lebensqual|patient.?reported|fragebogen|psycho|eq-?5d|promis|sexual")
row("adherence", "Therapy adherence", "FollowUp", "follow-up", MON, "adherent / not; reason",
    "Side-effect management; ET and neratinib continuation", f"{EBC};{MBC21}", carriage=BYREF, probe=r"adhär|adher|compliance|therapietreue")
row("prognosis_score", "Prognostic composite scores (DS-GPA, prognosis estimate)", "FollowUp", "other", PROG,
    "DS-GPA from subtype, age, progression, extracranial status, number of brain metastases; expected survival",
    "Brain metastasis treatment decisions; fertility counselling context", MBC, carriage=DERIVED,
    probe=r"ds-?gpa|prognos", note="Composite of subtype, age, brain metastasis and progression rows.")

# ----- Process ------------------------------------------------------------
row("mdt", "Multidisciplinary team discussion (date, recommendation)", "Process", "other", REC,
    "held / not; date; recommendation", "Prerequisite for stage IV with intact primary, OMD, bone metastases, intrathecal therapy, ALND vs RT", f"{EBC};{MBC}",
    carriage=NEWMOD, probe=r"tumorkonferenz|tumou?r board|\bmdo\b|multidisciplin|\bmdt\b")
row("trial", "Clinical trial participation / availability", "Process", "other", REC,
    "enrolled / available", "Preferred option whenever available; justifies genomic profiling", f"{EBC};{MBC}",
    carriage=NEWMOD, probe=r"studie|trial")
row("drug_availability", "Drug availability and regulatory status (EMA/FDA)", "Process", "other", PRED,
    "available / not; approved / not", "Alternative choices throughout the MBC algorithms", f"{MBC};{MBC21}",
    carriage=PROCESS, probe=r"zulassung|approval|off.?label")
row("care_setting", "Treating institution (specialised breast unit)", "Process", "other", REC, "breast unit / other",
    "Care quality principle", EBC, carriage=PROCESS, probe=r"einrichtung|abteilung|instelling|zentrum|centre|center")
row("patient_education", "Information and education delivered (verbal and written, side-effect management)", "Process", "other", REC,
    "delivered / documented", "Mandatory part of every treatment plan", f"{EBC};{MBC}", carriage=PROCESS, probe=r"aufklärung|voorlichting|education|information provided")


# ---------------------------------------------------------------------------
def load_hub():
    rows = list(csv.DictReader(HUB.open(encoding="utf-8")))
    return {r["id"].replace("eccdm:", ""): r for r in rows}


def load_source(path: Path):
    out = []
    for r in csv.DictReader(path.open(encoding="utf-8")):
        text = " ".join(str(v) for k, v in r.items() if k != "id" and v)
        out.append((r.get("id", ""), r.get("element") or r.get("label") or r.get("id", ""), text))
    return out


def load_standard_coverage():
    """hub element -> {standard: best predicate rank}"""
    rank = {"skos:exactMatch": 4, "skos:closeMatch": 3, "skos:narrowMatch": 2, "skos:broadMatch": 2, "skos:relatedMatch": 1}
    cov = defaultdict(dict)
    for std, f in STANDARD_SETS.items():
        for r in csv.DictReader([l for l in (REPO / f).open(encoding="utf-8") if not l.startswith("#")], delimiter="\t"):
            o = r.get("object_id", "").replace("eccdm:", "")
            p = r.get("predicate_id", "")
            if o and p in rank:
                cov[o][std] = max(cov[o].get(std, 0), rank[p])
    return cov


def load_int_status():
    """hub element -> INT availability from the INT elements.csv presence column."""
    st = {}
    for r in csv.DictReader((REPO / INT_ELEMENTS).open(encoding="utf-8")):
        eid = r["id"].replace("intbr:", "")
        # INT ids are Model.Attribute with capitalised attribute; hub ids are Model.attribute
        model, _, attr = eid.partition(".")
        st[(model, attr.lower())] = r.get("available") or r.get("presence") or ""
    return st


def hub_key(el: str):
    model, _, attr = el.partition(".")
    return (model, attr.lower().replace(".", ""))


def main():
    hub = load_hub()
    cov = load_standard_coverage()
    int_rows = list(csv.DictReader((REPO / INT_ELEMENTS).open(encoding="utf-8")))
    int_status = {}
    for r in int_rows:
        eid = r["id"].replace("intbr:", "")
        model, _, attr = eid.partition(".")
        # the presence column name differs per extractor version; take the first yes/no-like column
        val = ""
        for k in ("available", "presence", "int_status", "status"):
            if r.get(k):
                val = r[k]; break
        int_status[(model, attr.lower())] = val
    sources = {k: load_source(REPO / v) for k, v in STANDARDS.items()}
    sources["INT"] = load_source(REPO / INT_ELEMENTS)
    int_values = [(r["id"], r.get("label", ""), r.get("label", "")) for r in csv.DictReader((REPO / INT_VALUES).open(encoding="utf-8"))]

    # ---- validate hub references
    for r in ROWS:
        for el, *_ in r["maps"]:
            if el not in hub:
                sys.exit(f"unknown hub element {el} in row {r['key']}")
    keys = [r["key"] for r in ROWS]
    if len(keys) != len(set(keys)):
        sys.exit("duplicate keys: " + ", ".join(k for k, c in Counter(keys).items() if c > 1))
    # 2026-11-17: "by-reference" only defers the syntactic decision to the referenced resource.
    # Where the meaning needs structure a code cannot carry (biomarkers, genetics, pathology,
    # imaging) the class is new-module; elsewhere a generic coded finding suffices.
    for r in ROWS:
        if r["carriage"] == BYREF:
            r["carriage"] = NEWMOD if r["model"] in ("Biomarker", "Genetic", "Pathology", "Imaging") else CODED

    # ---- elements.csv
    OUT_ELEMENTS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_ELEMENTS.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "model", "element", "label", "cardinality", "type", "definition",
                    "category", "role", "value_domain", "decision", "guidelines", "hub_carriage"])
        for r in ROWS:
            carriage = r["carriage"] or ("hub" if r["maps"] else "")
            w.writerow([f"esmo:{r['model']}.{r['key']}", r["model"], r["key"], r["label"], "", "",
                        (r["value_domain"] + (" — " + r["note"] if r["note"] else "")),
                        r["category"], r["role"], r["value_domain"], r["decision"], r["guidelines"], carriage])

    # ---- SSSOM
    header = [
        "# curie_map:",
        '#   skos: "http://www.w3.org/2004/02/skos/core#"',
        '#   semapv: "https://w3id.org/semapv/vocab/"',
        '#   eccdm: "https://hl7.eu/fhir/ig/cancer-common/element/"',
        '#   esmo: "https://w3id.org/cancer-crosswalk/sources/esmo-breast/element/"',
        '# mapping_set_id: "https://w3id.org/cancer-crosswalk/mappings/esmo-breast__to__eccdm"',
        '# mapping_set_title: "ESMO breast cancer CPG data points -> ECCDM element crosswalk"',
        '# mapping_set_version: "0.1.0"',
        '# license: "https://creativecommons.org/licenses/by/4.0/"',
        '# mapping_tool: "semantic proposal (review pending)"',
        '# mapping_provider: "https://w3id.org/cancer-crosswalk"',
        '# subject_source: "https://www.esmo.org/guidelines/breast-cancer"',
        '# subject_source_version: "Loibl 2024 (10.1016/j.annonc.2023.11.016); de Azambuja 2026 (10.1016/j.annonc.2026.05.707)"',
        '# object_source: "https://hl7.eu/fhir/ig/cancer-common"',
        '# comment: "Subjects are data points that ESMO recommendations depend on (a requirement source, not a dataset). Rows exist only for data points with a hub element; the elements.csv hub_carriage column classifies the rest."',
    ]
    cols = ["subject_id", "subject_label", "subject_terminology", "source_context", "predicate_id", "object_id", "object_label",
            "mapping_cardinality", "element_kind", "mapping_justification", "confidence", "review_status", "comment"]
    n_map = 0
    with OUT_MAPPING.open("w", encoding="utf-8", newline="") as f:
        f.write("\n".join(header) + "\n")
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(cols)
        for r in ROWS:
            for el, pred, conf, cmt in r["maps"]:
                h = hub[el]
                w.writerow([f"esmo:{r['model']}.{r['key']}", r["label"], "—", f"{r['guidelines']}; {r['role']}", pred, f"eccdm:{el}",
                            h["label"], "1:n" if len(r["maps"]) > 1 else "1:1", "guideline-dependency",
                            "semapv:ManualMappingCuration", f"{conf:.2f}", "proposed",
                            (cmt + (" " if cmt and r["note"] else "") + (r["note"] if r["note"] else "")).strip() or f"Drives: {r['decision']}"])
                n_map += 1

    # ---- probes
    def hits(src_rows, rx):
        if not rx:
            return []
        c = re.compile(rx, re.I)
        return [lbl for _, lbl, text in src_rows if c.search(text)]

    probe = {}
    for r in ROWS:
        probe[r["key"]] = {k: hits(v, r["probe"]) for k, v in sources.items()}
        probe[r["key"]]["INT values"] = hits(int_values, r["probe"])

    # ---- report
    RANKNAME = {4: "exact", 3: "close", 2: "narrow/broad", 1: "related", 0: ""}
    def best_pred(maps):
        order = {E: 4, C: 3, N: 2, B: 2, R: 1}
        return max((order[p] for _, p, *_ in maps), default=0)

    def home_class(r):
        b = best_pred(r["maps"])
        if b >= 3: return "hub (exact/close)"
        if b == 2: return "hub (narrow/broad)"
        if b == 1: return "derivable / related"
        return "no hub home"

    by_role = defaultdict(Counter)
    by_carriage = Counter()
    for r in ROWS:
        by_role[r["role"]][home_class(r)] += 1
        if home_class(r) == "no hub home":
            by_carriage[r["carriage"]] += 1

    hub_needed = sorted({el for r in ROWS for el, p, *_ in r["maps"] if p in (E, C, N, B)})
    int_present = 0
    int_lookup = {}
    for r in int_rows:
        eid = r["id"].replace("intbr:", "")
        m, _, a = eid.partition(".")
        int_lookup[(m, a.lower())] = r
    def int_state(el):
        m, _, a = el.partition(".")
        rr = int_lookup.get((m, a.lower().replace(".", "")))
        if rr is None:
            # nested stage.code / stage.value
            rr = int_lookup.get((m, a.split(".")[0].lower()))
        if rr is None:
            return "?"
        for k in ("available", "presence", "status"):
            if rr.get(k):
                return rr[k]
        return "?"

    L = []
    L.append("# ESMO breast cancer guidelines as a requirement source — data points vs ECCDM, INT and the four standards\n")
    L.append("Generated by `scripts/build_esmo_source.py` from the curated table in that script. "
             "Each row is a data point that a recommendation in an ESMO Clinical Practice Guideline depends on, "
             "consolidated from three traceable extractions (`sources/esmo-breast/ref/*-datapoints.md`, git-ignored with the texts):\n")
    L.append("- **EBC2024** — Loibl S et al. *Early breast cancer: ESMO CPG for diagnosis, treatment and follow-up.* Ann Oncol 2024;35(2):159-182, doi:10.1016/j.annonc.2023.11.016 (Open Archive; main text, 190 extracted rows).")
    L.append("- **MBC2026** — de Azambuja E et al. *Metastatic breast cancer: ESMO CPG for diagnosis, treatment and follow-up.* Ann Oncol 2026;37(9):1203-1219, doi:10.1016/j.annonc.2026.05.707 (main text, 158 extracted rows; its supplement holds the diagnostic detail and was not captured).")
    L.append("- **MBC2021** — Gennari A et al. Ann Oncol 2021;32(12):1475-1495, doi:10.1016/j.annonc.2021.09.019 (superseded by MBC2026; accepted manuscript, 130 extracted rows; cited only where the 2026 main text defers detail to its supplement).\n")
    L.append(f"Consolidated: **{len(ROWS)} data points**, **{n_map} SSSOM rows** to the hub. "
             "Columns: *hub home* = best predicate of the SSSOM rows (exact/close = the hub carries it; narrow/broad = the hub carries a coarser or finer concept; "
             "related = derivable from hub elements; none = no hub element). *carriage* classifies the data points the hub does not carry, using the classes of `docs/extension-modules.md` plus `derived` (computable from hub elements) and `process`. "
             "*INT* = availability of the mapped hub element in the INT Milan workbook. *standards* = which of oBDS / NABON / B1MG / Senologie map to that hub element (from the existing SSSOM sets), "
             "and, for every row, which source element lists match the row's keyword probe (`probe:` column, hit counts; a count is a lead, not a mapping).\n")

    L.append("## Summary\n")
    L.append("| role | hub (exact/close) | hub (narrow/broad) | derivable / related | no hub home | total |")
    L.append("|---|---|---|---|---|---|")
    for role in [PRED, PROG, DIAG, REC, MON]:
        c = by_role[role]
        L.append(f"| {role} | {c['hub (exact/close)']} | {c['hub (narrow/broad)']} | {c['derivable / related']} | {c['no hub home']} | {sum(c.values())} |")
    tot = Counter()
    for c in by_role.values(): tot.update(c)
    L.append(f"| **all** | {tot['hub (exact/close)']} | {tot['hub (narrow/broad)']} | {tot['derivable / related']} | {tot['no hub home']} | {len(ROWS)} |\n")
    L.append("Data points with no hub home, by carriage class:\n")
    L.append("| carriage | n |\n|---|---|")
    for k, v in by_carriage.most_common():
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append(f"Hub elements the guidelines need (exact/close/narrow/broad rows): **{len(hub_needed)} of {len(hub)}**. "
             "Of these, INT availability: " + ", ".join(f"{s} {n}" for s, n in Counter(int_state(e) for e in hub_needed).most_common()) + ".\n")

    # predictive gaps list
    L.append("## Predictive data points without a hub home\n")
    L.append("These are the items that select a treatment in the guidelines and that ECCDM cannot carry today.\n")
    L.append("| data point | guideline | decision it drives | carriage | oBDS | NABON | B1MG | Senologie | INT |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in ROWS:
        if r["role"] == PRED and home_class(r) == "no hub home":
            p = probe[r["key"]]
            L.append(f"| {r['label']} | {r['guidelines']} | {r['decision']} | {r['carriage']} | "
                     + " | ".join(str(len(p[s])) if p[s] else "" for s in ("oBDS", "NABON", "B1MG", "Senologie"))
                     + f" | {len(p['INT']) + len(p['INT values']) or ''} |")
    L.append("")

    # full table by model
    L.append("## All data points\n")
    L.append("Standards column: letters mark which standard maps to the hub element (o = oBDS, N = NABON, B = B1MG, S = Senologie) with the best predicate rank in brackets; "
             "`probe:` gives keyword hit counts per source element list (o/N/B/S/I, I = INT elements + value labels).\n")
    for model in dict.fromkeys(r["model"] for r in ROWS):
        L.append(f"### {model}\n")
        L.append("| data point | role | guideline | value domain | hub element(s) | hub home | INT | standards | carriage |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for r in ROWS:
            if r["model"] != model:
                continue
            p = probe[r["key"]]
            probe_txt = "probe: " + "/".join(str(len(p[s])) for s in ("oBDS", "NABON", "B1MG", "Senologie")) + "/" + str(len(p["INT"]) + len(p["INT values"]))
            if r["maps"]:
                els = "<br>".join(f"`{el}` {p_}" for el, p_, *_ in r["maps"])
                ints = ", ".join(sorted({int_state(el) for el, p_, *_ in r["maps"] if p_ != R})) or "—"
                stds = set()
                for el, p_, *_ in r["maps"]:
                    if p_ == R: continue
                    for s, rk in cov.get(el, {}).items():
                        stds.add(f"{s[0]}[{RANKNAME[rk]}]")
                std_txt = " ".join(sorted(stds)) or "—"
            else:
                els, ints, std_txt = "—", "—", "—"
            L.append(f"| {r['label']} | {r['role']} | {r['guidelines']} | {r['value_domain']} | {els} | {home_class(r)} | {ints} | {std_txt}<br>{probe_txt} | {r['carriage'] or 'hub'} |")
        L.append("")

    L.append("## Reading the probe counts\n")
    L.append("The probe is a per-row regular expression run over each source's element list (element path, label, definition); it is a lead for the curator, not a mapping. "
             "Zero hits in every column means none of the five sources names the concept; hits in INT come from its 68 ECCDM-attribute rows and 276 local code labels, so INT can only hit items that ECCDM itself has.\n")
    OUT_DOC.write_text("\n".join(L) + "\n", encoding="utf-8")

    # debug: probe hits
    dbg = REPO / "sources" / "esmo-breast" / "ref" / "probe-hits.txt"
    with dbg.open("w", encoding="utf-8") as f:
        for r in ROWS:
            f.write(f"== {r['key']}  /{r['probe']}/\n")
            for s, h in probe[r["key"]].items():
                if h:
                    f.write(f"   {s}: {len(h)}: {'; '.join(h[:8])}\n")
    print(f"{len(ROWS)} data points, {n_map} mapping rows -> {OUT_ELEMENTS.relative_to(REPO)}, {OUT_MAPPING.relative_to(REPO)}, {OUT_DOC.relative_to(REPO)}")
    print("summary:", dict(tot), "| no-home by carriage:", dict(by_carriage), "| hub elements needed:", len(hub_needed))


if __name__ == "__main__":
    main()
