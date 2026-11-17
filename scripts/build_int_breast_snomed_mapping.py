#!/usr/bin/env python3
"""Build the INT Breast local-code -> SNOMED CT mapping set (SSSOM).

The curated table below maps every local code parsed into
``sources/int-breast/values.csv`` (by ``value_list`` and ``code``) to a SNOMED CT
concept, or records ``sssom:NoTermFound``. Object labels (FSNs) are fetched
from a Snowstorm at build time so the file never carries a mistyped label;
``scripts/verify_snomed_mapping.py`` re-checks the result independently.

Direction: subject (INT local code) <predicate> object (SNOMED CT concept).
The extra column ``hub_element`` names the ECCDM element the coded value would
feed, so the file doubles as the code-level companion of the element-level
``*__to__eccdm`` sets.

SKOS predicates follow SSSOM semantics: ``skos:broadMatch`` = object is
broader than the subject; ``skos:narrowMatch`` = object is narrower.

Usage:
    python scripts/build_int_breast_snomed_mapping.py \
        [--snowstorm http://localhost:8090] [--branch MAIN/2026-10-01]
"""
from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
VALUES = REPO / "sources" / "int-breast" / "values.csv"
OUT = REPO / "mappings" / "int-breast__values__to__snomed.sssom.tsv"

EXACT, CLOSE, BROAD, NARROW = "skos:exactMatch", "skos:closeMatch", "skos:broadMatch", "skos:narrowMatch"
NOTERM = "sssom:NoTermFound"
UNKNOWN = "261665006"      # Unknown (qualifier value)
NOT_APPLICABLE = "385432009"
NOT_DONE_SIT = "416237000"  # Procedure not done (situation)

# (element, value_list, code) -> (predicate, sctid|None, hub_element, confidence, comment)
# `element` is "" for lists whose key is unique in the workbook; lists that
# share a key across elements (SexAtBirth and TumourGradeValue both parse to
# "code") are keyed by element so one table cannot overwrite the other.
M: dict[tuple[str, str, str], tuple[str, str | None, str, float, str]] = {}


def add(vlist: str, rows: list[tuple], element: str = ""):
    for code, pred, sct, hub, conf, comment in rows:
        key = (element, vlist, str(code))
        if key in M:
            raise SystemExit(f"duplicate mapping key {key}")
        M[key] = (pred, sct, hub, conf, comment)


# ---- CancerPatient.SexAtBirth ------------------------------------------------
add("code", [
    ("1", EXACT, "248153007", "CancerPatient.sexAtBirth", 0.95, "sex=male"),
    ("2", EXACT, "248152002", "CancerPatient.sexAtBirth", 0.95, "sex=female"),
    ("9", CLOSE, UNKNOWN, "CancerPatient.sexAtBirth", 0.7,
     "No sex-specific 'unknown' finding in the International Edition; in FHIR prefer dataAbsentReason=unknown."),
], element="SexAtBirth")
# ---- CancerConditionAtDiagnosis.TumourGradeValue ----------------------------
GRADE_HUB = "CancerConditionAtDiagnosis.tumourGradeValue"
GRADE_NOTE = ("INT grade system 'SEER and ICD-O' = ICD-O-3 differentiation code; mapped to the system-agnostic "
              "G1-G4 qualifier values. If INT confirms Nottingham grading, use 1287024003 ff. instead.")
add("code", [
    ("1", EXACT, "1155701009", GRADE_HUB, 0.9, GRADE_NOTE),
    ("2", EXACT, "1155703007", GRADE_HUB, 0.9, GRADE_NOTE),
    ("3", EXACT, "1155704001", GRADE_HUB, 0.9, GRADE_NOTE),
    ("4", EXACT, "1155702002", GRADE_HUB, 0.9, GRADE_NOTE),
    ("5", EXACT, None, GRADE_HUB, 0.0,
     "Intermediate range 'I-II' has no SNOMED grade; nearest is 405986005 |Intermediate grade histologic differentiation| but that denotes G2, not a range."),
    ("6", EXACT, None, GRADE_HUB, 0.0, "Range 'II-III' has no SNOMED grade (see code 5)."),
    ("9", CLOSE, UNKNOWN, GRADE_HUB, 0.7,
     "'Unknown' is data-missing, not GX |cannot be assessed| (1155705000); keep as unknown."),
], element="TumourGradeValue")

# ---- CancerStage.Value: clinical T (two lists) and clinical N -----------------
T_HUB, N_HUB = "CancerStage.stage.value (T, clinical)", "CancerStage.stage.value (N, clinical)"
TNM_NOTE = "UICC qualifier values chosen (European hub); AJCC twins exist, e.g. AJCC cT1 = 1228889001."
T_ROWS = [
    ("0", EXACT, "1352975000", T_HUB, 0.9, "Tx. " + TNM_NOTE),
    ("1", EXACT, "1352986003", T_HUB, 0.9, "T0"),
    ("2", EXACT, "1352984000", T_HUB, 0.9, "Tis (DCIS/LCIS/Paget not split by INT)"),
    ("10", EXACT, "1352996007", T_HUB, 0.9, "T1 NOS"),
    ("11", EXACT, "1352979006", T_HUB, 0.9, "T1mic = T1mi"),
    ("12", EXACT, "1352983006", T_HUB, 0.9, "T1a"),
    ("13", EXACT, "1352968001", T_HUB, 0.9, "T1b"),
    ("14", EXACT, "1352973007", T_HUB, 0.9, "T1c"),
    ("20", EXACT, "1352993004", T_HUB, 0.9, "T2"),
    ("30", EXACT, "1352966002", T_HUB, 0.9, "T3"),
    ("40", EXACT, "1352997003", T_HUB, 0.9, "T4 NOS"),
    ("41", EXACT, "1352982001", T_HUB, 0.9, "T4a"),
    ("42", EXACT, "1352960008", T_HUB, 0.9, "T4b"),
    ("43", EXACT, "1352980009", T_HUB, 0.9, "T4c"),
    ("44", EXACT, "1352963005", T_HUB, 0.9, "T4d"),
    ("88", CLOSE, "385660001", T_HUB, 0.6, "'Not done' is not a T category; FHIR: omit the component or dataAbsentReason=not-performed."),
    ("99", CLOSE, UNKNOWN, T_HUB, 0.6, "Not a T category; data-absent."),
]
add("cT_imaging", T_ROWS)
add("cT_mammo", T_ROWS + [
    ("3", CLOSE, "27931000119107", "Imaging (finding), not CancerStage", 0.6,
     "Microcalcifications is an imaging finding, not a T category; INT list conflates mammography result with cT."),
])
add("cN", [
    ("0", EXACT, "1353039008", N_HUB, 0.9, "Nx. " + TNM_NOTE),
    ("1", EXACT, "1353041009", N_HUB, 0.9, "N0"),
    ("11", EXACT, "1356757005", N_HUB, 0.9, "N0(sn)"),
    ("20", EXACT, "1353043007", N_HUB, 0.9, "N1 NOS"),
    ("21", EXACT, "1353045000", N_HUB, 0.9, "N1mic = N1mi"),
    ("22", EXACT, "1353046004", N_HUB, 0.9, "N1a"),
    ("23", EXACT, "1353048003", N_HUB, 0.9, "N1b"),
    ("24", EXACT, "1353044001", N_HUB, 0.9, "N1c"),
    ("30", EXACT, "1353047008", N_HUB, 0.9, "N2 NOS"),
    ("31", EXACT, "1353050006", N_HUB, 0.9, "N2a"),
    ("32", EXACT, "1353055001", N_HUB, 0.9, "N2b"),
    ("40", EXACT, "1353053008", N_HUB, 0.9, "N3 NOS"),
    ("41", EXACT, "1353057009", N_HUB, 0.9, "N3a"),
    ("42", EXACT, "1353054002", N_HUB, 0.9, "N3b"),
    ("43", EXACT, "1353051005", N_HUB, 0.9, "N3c"),
    ("50", CLOSE, "399374009", N_HUB, 0.7, "'N+ NOS' is not a TNM category; mapped to the node-positive finding."),
    ("88", EXACT, None, N_HUB, 0.0, "'In situ' is not an N value; probably a list artefact — ask INT."),
    ("99", CLOSE, UNKNOWN, N_HUB, 0.6, "Not an N category; data-absent."),
])
# ---- CancerPatient.ComorbiditiesAtCancerDiagnosis ---------------------------
CO = "CancerPatient.comorbiditiesAtCancerDiagnosis"
add("comorbidity", [
    ("1", EXACT, "73211009", CO, 0.9, "Type not recorded by INT."),
    ("2", EXACT, "38341003", CO, 0.9, ""),
    ("3", EXACT, "13644009", CO, 0.95, ""),
    ("4", EXACT, "302870006", CO, 0.95, ""),
    ("5", CLOSE, "83469008", CO, 0.7, "'Insulinemia' read as hyperinsulinaemia; confirm with INT."),
    ("6", EXACT, "370992007", CO, 0.95, ""),
    ("7", EXACT, "237602007", CO, 0.9, ""),
    ("8", EXACT, "266987004", CO, 0.85, "Site and date of the previous cancer travel as a separate Condition, not in this code."),
])
# ---- Imaging.Type: mammography / ultrasound status variables -----------------
IM = "Imaging.type"
add("mammography", [
    ("0", CLOSE, NOT_APPLICABLE, IM, 0.6, ""),
    ("10", EXACT, "24623002", IM, 0.9, ""),
    ("11", CLOSE, "24623002", IM, 0.7, "Opportunistic screening is still screening mammography; organised vs opportunistic is not a SNOMED distinction."),
    ("12", BROAD, "71651007", IM, 0.7, "No 'diagnostic mammography' concept; parent Mammography."),
    ("19", EXACT, "71651007", IM, 0.9, ""),
    ("20", CLOSE, NOT_DONE_SIT, IM, 0.6, "FHIR: Procedure.status=not-done with code 71651007."),
    ("88", EXACT, None, IM, 0.0, "'Not collected' is a data-absent reason, not a concept."),
    ("99", CLOSE, UNKNOWN, IM, 0.6, ""),
])
add("ultrasound", [
    ("0", CLOSE, NOT_APPLICABLE, IM, 0.6, ""),
    ("19", CLOSE, "47079000", IM, 0.7, "Assumes breast ultrasound (variable sits beside mammography); generic 16310003 if not."),
    ("20", CLOSE, NOT_DONE_SIT, IM, 0.6, "FHIR: Procedure.status=not-done."),
    ("88", EXACT, None, IM, 0.0, "Data-absent reason."),
    ("99", CLOSE, UNKNOWN, IM, 0.6, ""),
])
# ---- Imaging.Type: M-staging examinations -----------------------------------
add("m_staging_exam", [
    ("10", EXACT, "41747008", IM, 0.95, ""),
    ("20", CLOSE, "45036003", IM, 0.85, "'Complete' abdominal US has no distinct concept."),
    ("21", EXACT, "105377009", IM, 0.95, ""),
    ("22", EXACT, "241453007", IM, 0.9, ""),
    ("23", CLOSE, "429915000", IM, 0.85, ""),
    ("24", CLOSE, "24848001", IM, 0.75, "Lower abdomen read as pelvis."),
    ("30", EXACT, "82918005", IM, 0.95, ""),
    ("40", EXACT, "241686001", IM, 0.9, "DXA is not a staging examination; kept because INT lists it."),
    ("50", BROAD, "441986001", IM, 0.5, "'Brain examination' assumed to mean brain imaging; modality unknown."),
    ("51", EXACT, None, IM, 0.0, "'Cervix uteri examination' ambiguous (gynaecological exam, cytology or imaging)."),
    ("60", EXACT, "55965002", IM, 0.9, ""),
    ("61", EXACT, "1290640000", IM, 0.9, ""),
    ("62", EXACT, "399208008", IM, 0.95, ""),
    ("63", EXACT, "713021002", IM, 0.95, ""),
    ("64", EXACT, "241075002", IM, 0.95, ""),
    ("65", EXACT, "713023004", IM, 0.95, ""),
    ("66", EXACT, "1295209004", IM, 0.95, ""),
    ("67", EXACT, "1295210009", IM, 0.9, ""),
    ("68", EXACT, "713028008", IM, 0.95, ""),
    ("69", EXACT, "1295429000", IM, 0.9, ""),
    ("70", EXACT, "241645008", IM, 0.95, ""),
    ("71", EXACT, "2690005", IM, 0.95, ""),
    ("72", EXACT, "427366006", IM, 0.95, ""),
    ("73", EXACT, "6007000", IM, 0.95, ""),
    ("74", EXACT, "241621009", IM, 0.95, ""),
    ("75", EXACT, "816077007", IM, 0.95, ""),
    ("80", EXACT, "169072007", IM, 0.9, ""),
    ("81", EXACT, "241577003", IM, 0.95, ""),
    ("82", EXACT, "169069000", IM, 0.95, ""),
    ("83", EXACT, "169070004", IM, 0.95, ""),
    ("84", EXACT, "34227000", IM, 0.95, ""),
    ("85", EXACT, "169068008", IM, 0.95, ""),
    ("86", EXACT, "241540006", IM, 0.95, ""),
    ("90", EXACT, "86273004", "(not Imaging) procedure", 0.8, "A biopsy is not an imaging procedure; INT lists it among M-staging examinations."),
    ("98", EXACT, "1352512001", "CancerStage.stage.value (M, clinical)", 0.9, "'Clinically M0' is a stage value, not an examination; UICC cM0."),
    ("99", BROAD, "363679005", IM, 0.5, "Type unknown -> generic Imaging."),
])
# ---- Imaging.BodySite --------------------------------------------------------
IB = "Imaging.bodySite"
add("site", [
    ("breast", EXACT, "76752008", IB, 0.95, ""),
    ("neck", EXACT, "45048000", IB, 0.95, ""),
    ("brain", EXACT, "12738006", IB, 0.95, ""),
    ("lung", EXACT, "39607008", IB, 0.95, ""),
    ("chest_thorax", EXACT, "51185008", IB, 0.9, ""),
    ("abdomen", EXACT, "818983003", IB, 0.9, "Synonym 'Abdomen'; the FSN is the long abdominopelvic-cavity term."),
    ("lower_abdomen", EXACT, "27033000", IB, 0.9, ""),
    ("liver", EXACT, "10200004", IB, 0.95, ""),
    ("pelvis", EXACT, "12921003", IB, 0.9, ""),
    ("cervix_uteri", EXACT, "71252005", IB, 0.95, ""),
    ("spine", EXACT, "421060004", IB, 0.9, ""),
    ("femur", EXACT, "71341001", IB, 0.95, ""),
    ("upper_limbs", EXACT, "53120007", IB, 0.9, ""),
    ("skull", CLOSE, "89546000", IB, 0.85, "Skull as bone of cranium."),
    ("sternum", EXACT, "56873002", IB, 0.95, ""),
    ("rib_cage_thoracic_skeleton", EXACT, "60413009", IB, 0.9, ""),
    ("scapula", EXACT, "79601000", IB, 0.95, ""),
    ("skeleton_bone", CLOSE, "113192009", IB, 0.8, "Alternative 272673000 |Bone structure| when a single bone is meant."),
    ("whole_body", EXACT, "38266002", IB, 0.9, ""),
])
# ---- Radiotherapy.BodySite ---------------------------------------------------
RB = "Radiotherapy.bodySite"
add("rt_site", [
    ("10", EXACT, "76752008", RB, 0.95, ""),
    ("11", EXACT, "73056007", RB, 0.95, ""),
    ("12", EXACT, "80248007", RB, 0.95, ""),
    ("13", BROAD, "76752008", RB, 0.5, "Post-surgical residual breast tissue has no concept; parent Breast structure."),
    ("15", EXACT, "91470000", RB, 0.9, ""),
    ("16", EXACT, "19654004", RB, 0.9, ""),
    ("17", EXACT, "20437008", RB, 0.9, ""),
    ("20", EXACT, "77621008", RB, 0.9, ""),
    ("21", CLOSE, "1401545008", RB, 0.8, "Only the lateralised fossa exists, not the region."),
    ("22", CLOSE, "1401543001", RB, 0.8, "Only the lateralised fossa exists, not the region."),
    ("30", EXACT, "79601000", RB, 0.95, ""),
    ("31", EXACT, "719628000", RB, 0.95, ""),
    ("32", EXACT, "719627005", RB, 0.95, ""),
    ("40", EXACT, "78904004", RB, 0.95, ""),
    ("41", EXACT, "771319006", RB, 0.9, ""),
    ("42", EXACT, "771318003", RB, 0.9, ""),
    ("50", EXACT, "113197003", RB, 0.9, ""),
    ("51", EXACT, "724221004", RB, 0.9, ""),
    ("52", EXACT, "724223001", RB, 0.9, ""),
    ("60", EXACT, "71341001", RB, 0.95, ""),
    ("61", EXACT, "722739008", RB, 0.95, ""),
    ("62", EXACT, "722738000", RB, 0.95, ""),
    ("63", EXACT, "12921003", RB, 0.9, ""),
    ("68", EXACT, "421060004", RB, 0.9, ""),
    ("69", EXACT, "272673000", RB, 0.9, ""),
    ("70", EXACT, "12738006", RB, 0.95, ""),
    ("71", EXACT, "72410000", RB, 0.95, ""),
    ("80", CLOSE, NOT_APPLICABLE, RB, 0.6, ""),
    ("99", CLOSE, UNKNOWN, RB, 0.6, ""),
])
# ---- Surgery (INT puts the procedure list under Surgery.BodySite) ------------
SP = "(no ECCDM slot) Surgery procedure code"
SP_NOTE = "ECCDM Surgery has bodySite but no procedure type; this maps the procedure itself (FHIR Procedure.code). "
add("procedure", [
    ("0", CLOSE, NOT_DONE_SIT, SP, 0.6, SP_NOTE + "Negation: FHIR Procedure.status=not-done."),
    ("1", BROAD, "234262008", SP, 0.6, SP_NOTE + "Sentinel biopsy (1179695007) vs axillary dissection (79544006) not distinguishable."),
    ("19", CLOSE, "122548005", SP, 0.8, "Assumes breast biopsy."),
    ("21", CLOSE, "64368001", SP, 0.8, "'Breast gland resection' read as partial excision of breast."),
    ("22", EXACT, "307796007", SP, 0.9, ""),
    ("23", EXACT, None, SP, 0.0, "'Extra-mammary tissue resection' ambiguous: accessory/ectopic breast tissue (770108008) or skin (72432009)."),
    ("24", CLOSE, "72577009", SP, 0.8, "Nipple-areola complex; SNOMED concept covers the nipple."),
    ("25", EXACT, "395165008", SP, 0.95, ""),
    ("28", EXACT, "237372000", SP, 0.9, ""),
    ("29", BROAD, "392023007", SP, 0.6, "Resection NOS."),
    ("31", EXACT, "172049005", SP, 0.95, ""),
    ("41", CLOSE, "1380209001", SP, 0.8, ""),
    ("42", EXACT, "428564008", SP, 0.95, ""),
    ("43", BROAD, "1231734007", SP, 0.5, "Only incision-specific skin-reducing concepts exist (1179093004 inverted-T, 1179092009 vertical)."),
    ("44", EXACT, "172043006", SP, 0.9, "Simple mastectomy = total mastectomy (synonym)."),
    ("45", EXACT, "384723003", SP, 0.95, ""),
    ("48", EXACT, "447421006", SP, 0.95, ""),
    ("49", EXACT, "1231734007", SP, 0.85, "Excision of breast = mastectomy NOS."),
    ("51", EXACT, None, SP, 0.0, "Electrochemotherapy has no SNOMED concept in the International Edition."),
    ("52", BROAD, "225148005", SP, 0.5, "Two procedures in one code; re-suture = 83550001."),
    ("71", EXACT, "302343007", SP, 0.9, ""),
    ("72", EXACT, "27315000", SP, 0.95, ""),
    ("73", CLOSE, "237406004", SP, 0.8, "Mammoplasty as plastic operation on the breast; reduction/augmentation/reconstruction not split."),
    ("74", EXACT, "387628008", SP, 0.95, ""),
    ("98", CLOSE, NOT_APPLICABLE, SP, 0.6, ""),
    ("99", BROAD, "392090004", SP, 0.5, "Type not specified -> Operation on breast."),
])
# ---- LastFollowUp: INT follow-up event type ----------------------------------
FU_NOTE = "INT event list mixes vital status, disease status and treatment events; hub needs a split across LastFollowUp and ClinicalCancerProgression. "
add("followup_event", [
    ("primary_tumor_for_inpatient_admissions_recurrence", CLOSE, "372137005", "CancerConditionAtDiagnosis", 0.7, FU_NOTE + "Uncoded first line of the INT list."),
    ("8", CLOSE, "447421006", "Surgery", 0.7, "Breast context assumed; generic 737301002."),
    ("9", EXACT, None, "Surgery", 0.0, "Completion surgery has no concept."),
    ("10", CLOSE, "314955001", "ClinicalCancerProgression.diseaseStatus=Recurrence, extentType=Loco-regional", 0.75, "Regional recurrence not covered by the local-recurrence concept."),
    ("11", EXACT, None, "ClinicalCancerProgression", 0.0, "No 'suspected recurrence' situation concept."),
    ("14", EXACT, None, "ClinicalCancerProgression", 0.0, "Suspicion ruled out; no concept."),
    ("15", CLOSE, "145501000119108", "ClinicalCancerProgression.metastaticSites", 0.75, "Contralateral laterality is relative; not encoded."),
    ("16", EXACT, None, "Surgery", 0.0, ""),
    ("17", EXACT, None, "Surgery", 0.0, ""),
    ("18", EXACT, None, "Surgery", 0.0, "'Negative primary surgery' meaning unclear."),
    ("20", EXACT, "399409002", "ClinicalCancerProgression.extentType=Metastatic", 0.9, ""),
    ("21", EXACT, None, "ClinicalCancerProgression", 0.0, "Only organ-specific suspected-metastasis situations exist (e.g. lung 317521000112104)."),
    ("30", BROAD, "109359008", "new CancerConditionAtDiagnosis", 0.5, ""),
    ("31", BROAD, "372137005", "new CancerConditionAtDiagnosis", 0.6, "Second primary in the contralateral breast = a new primary breast cancer; laterality lost."),
    ("39", EXACT, None, "", 0.0, "Other."),
    ("40", EXACT, "419099009", "LastFollowUp.vitalStatus=Dead", 0.95, ""),
    ("50", EXACT, "399307001", "(no ECCDM slot) LastFollowUp", 0.9, "ECCDM VitalStatus is Alive|Dead only; lost-to-follow-up has no hub value."),
    ("60", EXACT, "438949009", "LastFollowUp.vitalStatus=Alive", 0.95, ""),
    ("61", CLOSE, "110396000", "LastFollowUp.vitalStatus=Alive + evidenceOfDisease=false", 0.8, "Alternative 445150007 |Surviving free of recurrence|."),
    ("62", CLOSE, "110278006", "LastFollowUp.vitalStatus=Alive + evidenceOfDisease=true", 0.65, ""),
    ("99", CLOSE, UNKNOWN, "LastFollowUp.vitalStatus", 0.6, ""),
])
# ---- Radiotherapy intent -----------------------------------------------------
add("rt_type", [
    ("1", EXACT, "373846009", "Radiotherapy.setting=Postoperative/Adjuvant (intent implied Definitive)", 0.85,
     "INT 'type' mixes intent and setting; ECCDM Intent is Definitive|Palliative, so adjuvant lands in Setting."),
    ("2", EXACT, "363676003", "Radiotherapy.intent=Palliative", 0.95, ""),
    ("3", CLOSE, "255595002", "(no ECCDM value) Radiotherapy.intent", 0.5, "Cytoreductive has no intent concept; debulking action qualifier."),
    ("8", EXACT, None, "Radiotherapy.intent", 0.0, "Data-absent reason."),
    ("9", CLOSE, UNKNOWN, "Radiotherapy.intent", 0.6, ""),
])
# ---- SystemicTreatment: therapy class per status variable --------------------
THERAPY_CLASS = {
    "neoadj_chemo_status": (EXACT, "1259200004", "SystemicTreatment.type=chemotherapy + setting=Neoadjuvant", 0.9, ""),
    "adj_chemo_status": (BROAD, "367336001", "SystemicTreatment.type=chemotherapy + setting=Adjuvant", 0.7, "No 'adjuvant chemotherapy' concept; parent Chemotherapy, setting carries adjuvant."),
    "hormone_status": (CLOSE, "169413002", "SystemicTreatment.type=hormone therapy", 0.8, "Generic hormone therapy; antineoplastic endocrine therapy has no own concept."),
    "target_status": (NARROW, "1237262009", "SystemicTreatment.type=targeted therapy", 0.5, "No generic targeted-therapy concept; HER2 inhibitor therapy is the breast-relevant narrower concept."),
}
# ---- SystemicTreatment: workflow status codes (shared by the four lists) ------
ST = "(no ECCDM slot) SystemicTreatment status -> FHIR Procedure.status/statusReason"
STATUS = [
    ("1", CLOSE, "385651009", ST, 0.7, "Ongoing at INT; performer not encodable in the code."),
    ("2", CLOSE, "385651009", ST, 0.7, "Ongoing elsewhere (known)."),
    ("3", CLOSE, "385651009", ST, 0.7, "Ongoing elsewhere (unknown)."),
    ("4", CLOSE, "385658003", ST, 0.7, "Completed at INT."),
    ("5", CLOSE, "385658003", ST, 0.7, "Completed elsewhere (known)."),
    ("6", CLOSE, "385658003", ST, 0.7, "Completed elsewhere (unknown)."),
    ("7", EXACT, "416151008", ST, 0.85, ""),
    ("8", CLOSE, "385642001", ST, 0.75, ""),
    ("9", CLOSE, "762450006", ST, 0.6, "Age/comorbidity read as contraindication."),
    ("10", BROAD, "1296859006", ST, 0.5, "Refusal covered; death before treatment is not."),
    ("11", CLOSE, "428119001", ST, 0.75, ""),
    ("12", EXACT, None, ST, 0.0, "'Probably performed elsewhere' has no concept."),
    ("13", CLOSE, "410527000", ST, 0.6, "Proposed = offered; outcome unknown."),
    ("99", CLOSE, UNKNOWN, ST, 0.6, ""),
]
for lst in THERAPY_CLASS:
    add(lst, STATUS)

HEADER = [
    "subject_id", "subject_label", "source_context", "predicate_id", "object_id", "object_label",
    "hub_element", "mapping_justification", "confidence", "review_status", "comment",
]


def fetch_fsn(base: str, branch: str, sctid: str, cache: dict) -> str:
    if sctid not in cache:
        c = json.load(urllib.request.urlopen(f"{base}/{branch}/concepts/{sctid}", timeout=30))
        if not c.get("active"):
            raise SystemExit(f"inactive concept {sctid}")
        cache[sctid] = c["fsn"]["term"]
    return cache[sctid]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snowstorm", default="http://localhost:8090")
    ap.add_argument("--branch", default="MAIN/2026-10-01")
    ap.add_argument("--values", type=Path, default=VALUES)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    values = list(csv.DictReader(args.values.open(encoding="utf-8")))
    cache: dict[str, str] = {}
    out: list[dict] = []
    unmapped: list[str] = []

    def row(subject_id, subject_label, ctx, spec):
        pred, sct, hub, conf, comment = spec
        if sct is None:
            oid, olabel, pred_out, conf_out = NOTERM, "", EXACT, ""
        else:
            oid, olabel, pred_out, conf_out = f"sct:{sct}", fetch_fsn(args.snowstorm, args.branch, sct, cache), pred, f"{conf:.2f}"
        out.append({
            "subject_id": subject_id, "subject_label": subject_label, "source_context": ctx,
            "predicate_id": pred_out, "object_id": oid, "object_label": olabel, "hub_element": hub,
            "mapping_justification": "semapv:ManualMappingCuration", "confidence": conf_out,
            "review_status": "proposed", "comment": comment,
        })

    for v in values:
        code = v["code"] or v["id"].rsplit(".", 1)[1]
        spec = M.get((v["element"], v["value_list"], code)) or M.get(("", v["value_list"], code))
        if spec is None:
            unmapped.append(v["id"]); continue
        ctx = f"{v['model']}.{v['element']} / {v['value_list']}" + (f" = {v['code']}" if v["code"] else "")
        row(v["id"], v["label"], ctx, spec)
    # therapy-class rows for the four status variables
    headings = {"neoadj_chemo_status": "Status of neoadjuvant chemotherapy in relation to surgery",
                "adj_chemo_status": "Status of adjuvant chemotherapy, phase j",
                "hormone_status": "Hormone therapy status, phase j",
                "target_status": "Target therapy status, phase j"}
    for lst, spec in THERAPY_CLASS.items():
        row(f"intbr:SystemicTreatment.Type.{lst}", headings[lst], f"SystemicTreatment.Type / {lst} (variable)", spec)

    meta = f"""# curie_map:
#   skos: "http://www.w3.org/2004/02/skos/core#"
#   semapv: "https://w3id.org/semapv/vocab/"
#   sssom: "https://w3id.org/sssom/"
#   sct: "http://snomed.info/id/"
#   intbr: "https://w3id.org/cancer-crosswalk/sources/int-breast/element/"
# mapping_set_id: "https://w3id.org/cancer-crosswalk/mappings/int-breast__values__to__snomed"
# mapping_set_title: "INT Milan breast data warehouse local codes (ECCDM availability workbook 2026-10-30) -> SNOMED CT"
# mapping_set_version: "0.1.0"
# license: "https://creativecommons.org/licenses/by/4.0/"
# mapping_tool: "scripts/build_int_breast_snomed_mapping.py (curated table, FSNs fetched from Snowstorm)"
# mapping_provider: "https://w3id.org/cancer-crosswalk"
# subject_source: "https://w3id.org/cancer-crosswalk/sources/int-breast"
# object_source: "http://snomed.info/sct"
# object_source_version: "http://snomed.info/sct/900000000000207008/version/20261001"
# comment: "Direction: subject (INT local code, see sources/int-breast/values.csv) <predicate> object (SNOMED CT International Edition 2026-10-01). Code-level companion of the element-level *__to__eccdm sets. Non-standard ext cols: source_context (INT variable / value list = code), hub_element (ECCDM element the coded value would feed; '(no ECCDM slot)' marks hub gaps), review_status. object_id = sssom:NoTermFound records a local code with no SNOMED equivalent. skos:broadMatch = object broader than subject; skos:narrowMatch = object narrower. All FSNs verified against Snowstorm 11 / INT 20261001 by scripts/verify_snomed_mapping.py. Every row is 'proposed' and awaits clinical review by INT."
"""
    with args.out.open("w", encoding="utf-8", newline="") as f:
        f.write(meta)
        w = csv.DictWriter(f, fieldnames=HEADER, delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(out)
    from collections import Counter
    print(f"Wrote {args.out}: {len(out)} rows, {len(cache)} distinct SNOMED concepts")
    for p, n in Counter(r["predicate_id"] if r["object_id"] != NOTERM else "NoTermFound" for r in out).most_common():
        print(f"  {p}: {n}")
    if unmapped:
        print(f"UNMAPPED ({len(unmapped)}):"); [print("  ", u) for u in unmapped]
    return 1 if unmapped else 0


if __name__ == "__main__":
    raise SystemExit(main())
