#!/usr/bin/env python3
"""Inverse-gap analysis: source-side elements with NO ECCDM hub home.

Every unmapped field is placed in a named information category (see MODULES)
and classified by carriage — how ECCDM could carry it.

The hub coverage report (coverage.py) measures how much of ECCDM each source
fills. This does the opposite: it takes every source element that was NOT mapped
to the hub and clusters it into candidate **extension modules** (extension
modules ECCDM would need), classifying each by how it *could* be carried:

  carriage:
    by-reference       -> no hub field, but attachable as referenced evidence
                          IF ECCDM adds an evidence hook + an Observation/Finding
                          logical model (e.g. ER/PR/HER2, BI-RADS, pathology).
    new-module         -> needs a whole new hub model (e.g. tumour board / MDO).
    out-of-scope       -> administrative / genomics-infrastructure, not clinical
                          content ECCDM aims to model.

Reads sources/*/elements.csv + mappings/*__to__eccdm.sssom.tsv.
Writes docs/extension-modules.md and prints a summary.

Usage:
    python scripts/inverse_gaps.py [--out docs/extension-modules.md]
"""
from __future__ import annotations

import argparse
import csv
import glob
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
MAPPINGS = REPO / "mappings"
DEFAULT_OUT = REPO / "docs" / "extension-modules.md"

SOURCES = {
    "mii-onko-obds": "sources/mii-onko-obds/elements.csv",
    "nabon-mammacarcinoom": "sources/nabon-mammacarcinoom/elements.csv",
    "b1mg-cmd": "sources/b1mg-cmd/elements.csv",
    "senologie-datenkranz": "sources/senologie-datenkranz/elements.csv",
}

# ---------------------------------------------------------------------------
# Clustering
#
# Two passes per unmapped row:
#   1. keyword match on the element's OWN text (element path / label +
#      definition) against MODULES, in order (first match wins, specific
#      clinical clusters before catch-alls);
#   2. for generic leaves ("Datum", "Code", "Grad", "L", ...) whose label
#      carries no meaning, fall back to the parent CONTEXT (oBDS module and
#      XSD type, B1MG domain) so the leaf inherits its parent's cluster.
# Anything left is "Unclustered / to triage".
#
# carriage (how ECCDM could carry the field):
#   by-reference  attachable as a referenced Observation/Finding (data dictionary)
#   extend-model  attribute-level detail of an EXISTING hub model
#   new-module    needs a whole new hub model
#   out-of-scope  not clinical cancer content ECCDM targets
#   review        structural leaves whose context was lost in extraction
# ---------------------------------------------------------------------------
MODULES = [
    # --- not breast / not ECCDM content: catch first so organ-module items do
    #     not leak into pathology / surgery ---
    ("Other-entity & paediatric registry modules (prostate, colorectal, melanoma, DKKR)",
     "out-of-scope",
     ["gleason", "psa", "ldh", "rektum", "anokutan", "mesorektal", "melanom",
      "tumordicke", "ulzeration", "breslow", "prostat", "kolorekt", "stomaposition",
      "dkkr", "gpoh", "rasmutation", "stanze", "darm"]),
    ("Registry transport / XML structure", "out-of-scope",
     ["menge_", "meldung", "meldeanlass", "meldebegruend", "meldedatum", "meldevorgang",
      "kuerzel", "strukturiert", "zusatzitem", "modul_", " obds ", "einwilligung",
      "rate_type", "codeversion", "zertifizierung", "eigene_leistung", "unbekannt_nein",
      "oder_unbekannt", "nummersoort", "adressoort", "emailsoort", "naamgebruik"]),
    ("Genomics / biobank infrastructure", "out-of-scope",
     ["sample", "sequencing", "pipeline", "library", "aliquot", "biobank", "alignment",
      "file_format", "parentage", "variant_calling", "variant_annotation",
      "variant_interpretation", "matching", "matched", "normal_tumor", "tumor_normal",
      "anatomy"]),

    # --- clinical content with no hub field ---
    ("Study participation", "new-module",
     ["studie", "study", "trial"]),
    ("Tumour board / MDO", "new-module",
     ["tumorkonferenz", "tumorboard", "mdo", "konferenz", "advies", "beleid",
      "recommendation", "therapieempfehlung", "besluit", "aanwezigen", "voorzitter",
      "afwijken richtlijn", "motivatie", "vorstellung", "herbespreken", "vraagstelling",
      "aanvrager", "patientenwunsch", "conclusie", "aanmelding"]),
    ("Adverse events / complications", "new-module",
     ["nebenwirkung", "adverse", "toxicity", "ctcae", "meddra", "komplikation",
      "complicat", "komplpostop"]),
    ("Psychosocial / supportive care", "new-module",
     ["psychoonko", "sozialdienst", "maatschappelijk"]),
    ("Biomarker / receptor status", "by-reference",
     ["her2", "hormonrez", "oestrogen", "estrogen", "progesteron", "receptor",
      "rezeptor", "ki-67", "ki67", "pd-l1", "pdl1", "immunhisto", "allred", "irsscore",
      "irs-score", ".biomarker", "proliferatie"]),
    ("Molecular tests / genomics", "by-reference",
     ["oncotype", "mammaprint", "genexpress", "genetic", "genetik", "genetisch",
      "genmutatie", "genprofiel", "variant", "mutation", "sequenc", "genom",
      "moleculair", "gen_name"]),
    ("Clinical examination / performance status", "by-reference",
     ["klinischeuntersuchung", "palpation", "mamillenbefund", "hautveraend",
      "lichamelijk onderzoek", "performance", "leistungszustand", " asa ", "ecog",
      "karnofsky", "tumorformel", "clinical_status", "huidig probleem", "palpabel"]),
    ("Imaging findings / BI-RADS", "by-reference",
     ["bi-rads", "birads", " acr ", "acrdichte", "mammografie", "echografie", "mammograf", "massa",
      "calcificat", "aankleuring", "densiteit", "echogenic", "laesie", "beeldvormend",
      "radiolog", "mri", "echo", "enhancement", "cyste", "asymmetrie", "elasticit",
      "vascularisatie", "fibroglandulair", "implantaten", "ligging prothese",
      "geluidstransmissie", "projectierichting", "herdbefund", "mikrokalk", "bildgebung",
      "jodiumhoudend", "zichtbaar", "corpus alienum", "littekenweefsel", "vethoudende",
      "verdachte vorm", "typisch benigne", "geassocieerde bevindingen", "lymphangitis",
      "diepte van de afwijking", "locatie afwijking", "locatie benigne", "extravasaat",
      "houding van de pati", "posterieure", "dynamische curve", "cortexdikte",
      "gelokaliseerd", "niet aankleurende", "negatieve enhancement", "overige bevindingen",
      "achtergrondkleuring", "ct-diameter", "occulte", "solide", "orientatie",
      "oriëntatie", "specifieke diagnosen", "uitslag beeldvormend", "tussentijdse controle",
      "restcalcificaties", "intraoperativesimaging", "imaging", " positie ", " diameter ",
      " bevindingen "]),
    ("Pathology detail", "by-reference",
     ["resekt", "snijvlak", "margin", "sentinel", "schildwacht", "lymfeklier",
      "lymphknoten", "lk_", "lkratio", "invasief", "invasiv", "dcis", "nottingham",
      "mitose", "tubulus", "grading", " grad ", ".grad ", "graad", "praeparat",
      "specimen", "histolog", "angioinvasie", "cytologie", "representatief",
      "pathologie", "pathology", "probeneingang", "cpseg", "topklier", "extranodale",
      "residualstatus", "sicherheitsabstand", "huidinvasie", "tumordistributie",
      "tumorgroesse", "multifokal", "pt-diameter", "pn okselklier", "ypn okselklier",
      "mariklier", "intrammaire", "chemonutzen", "subtyp"]),
    ("Patient history / risk factors", "by-reference",
     ["menopau", "anamnese", "voorgeschied", "gravida", "schwangerschaft", "familie",
      "brca", "zwanger", "borstvoedend", "allergie", "nierfunctie", "smoking",
      "raucher", "age_at", "history", "erblich", "fruehere_tumorerkrankung",
      "eerdere behandelingen", "syndrom", "comorbid", "menarche", "hormonersatz",
      "exposure", "alcohol", "environmental"]),
    ("Diagnosis / staging detail (TNM, localisation, side)", "extend-model",
     ["tnm", "praefix", "_symbol", "stadium", "weitere_klassifikation", "fernmetastas",
      " metastas", "metastasierungsstadium", "diagnos", "primaertumor", "tumorzuordnung", "seitenlokalisation",
      "icd", "morphologie", "topograph", "zijde", " aandoening ", "probleem",
      "primaire tumor", "tumorlokalisation", "uhrzeit", "mamillenabstand",
      "afstand tot de tepel", " ct ", "yct", " pt ", "ypt", " pn ", "ypn", " cn ", "ycn",
      "resectabiliteit", "recidief", "lokalisation", "diagnose", " seite ", "diagnose.seite",
      "seitenlokalisation", "risicostatus",
      "tumormanifestation", "falltyp", "topology", "grade", "stage"]),

    ("Treatment detail (drug, dose, cycles, fractions, technique)", "extend-model",
     ["substanz", "atc", "dosis", "dosage", " dose", "fraktion", "fractions", "zyklus",
      "therapielinie", " line ", "protokoll", "protocol", "applikationsart",
      "strahlenart", "boost", "stereotak", "perkutan", "interstitiell",
      "atemgetriggert", "radiochemo", "ende_grund", "medikation", "drug", "cumulative",
      "duration", "modality", "modaliteit", "therapie", "therapy", "bestrahlung",
      "syst", "zielgebiet", "pre-treated", "intention", "switch", "vervolg",
      "neoadjuvant", "begleitmedikation", "quantity", "behandeling", "metabolisch",
      "treatment", "antibiotika"]),
    ("Surgery / procedure detail (biopsy, implants, planning)", "extend-model",
     ["reconstruct", "rekonstru", "drahtmark", "praeparatkontrolle", "stoma",
      "anastomose", "operatie", "resectie", "clavien", "operation", "operateur",
      " ops ", "eingriff", "biops", "biopt", "gauge", "marker", "drainage", "re-excisie",
      "huidsparend", "tepelsparend", "implantat", "implant", "interventie",
      "procedure", "lokalisatie", "postoperativ", "praeoperativ", "intraop",
      "chirurg", " op ", "resection", "opdauer", "oplagerung", "geplanteop"]),
    ("Follow-up, response, death & second tumour", "extend-model",
     ["todesurs", " tod ", "tod_", "death", "overlijden", "doodsoorzaak", "verlauf",
      "follow-up", "nachsorge", "vital", "outcome", "verloop", "respons ", "response",
      "tumorstatus", "zweittumor", "zweitttumor"]),

    # --- organisational context: who, where, how referred ---
    ("Referral / care setting", "out-of-scope",
     ["verwijz", "detectie", "zorgaanbieder", "zorgverlener", "specialisme",
      "einrichtung", "abteilung", "kontakt", "aanvullend onderzoek", "behandelaar",
      "kh_abt"]),
    ("Administrative / identifiers / contact", "out-of-scope",
     ["melder", "absender", "submitter", "versicherten", "adres", "ident", "steward",
      "consent", "einsende", "naam", "name", "vorname", "nachname", "titel", "strasse",
      "straat", "hausnummer", "huisnummer", " plz ", "postcode", " ort ", "woonplaats",
      "gemeente", " land ", "telefon", "email", "initialen", "roepnaam", "voorvoegsel",
      "partner", "meerling", "nummer", "country", "institution", "center", "publisher",
      "database", "iban", " bic ", "bsnr", "lanr", "zanr", "iknr", "krankenkasse",
      "beihilfe", "kontoinhaber", "bankname", "gueltig", "stammdaten", "ersatzkode",
      "geburtsname", "anschrift", "ansprechpartner", "projects", "publication",
      "consortia", " role ", "contactgegevens", "namensvorsatz", "namenszusatz"]),

    # --- structural leaves whose parent context was lost by flattening ---
    ("Generic sub-elements (date / type / code / value / free text)", "review",
     ["freetext", "freitext", "befundtext", "auspraegung", "prozentzahl",
      "additioneleinformatie", "toelichting", "anmerkung", "bemerkung", "sonstige",
      "unstrukturiert", "kodiertebefundaussage", "strukturierterbefund"]),
]
UNCLUSTERED = ("Unclustered / to triage", "review")
GENERIC_MODULE = "Generic sub-elements (date / type / code / value / free text)"

# labels that carry no meaning on their own -> classify by parent context
GENERIC_LEAVES = {
    "art", "typ", "type", "code", "datum", "date", "wert", "value", "einheit", "unit",
    "version", "bezeichnung", "name", "grad", "id", "description", "anmerkung",
    "bemerkung", "sonstige", "sonstiges", "freitext", "befundtext", "auspraegung",
    "sonstige_auspraegung", "prozentzahl", "additioneleinformatie", "toelichting",
    "status", "icd", "ops", "quantity", "line", "intent", "outcome", "modality",
    "duration", "protocol", "history", "procedures",
}

# parent context (oBDS module + XSD type, B1MG domain) -> module name.
# Matched as substrings of " <ctx> " (lower-cased), in order.
CONTEXT = [
    ("dkkr", "Other-entity & paediatric registry modules (prostate, colorectal, melanoma, DKKR)"),
    ("modul_darm", "Other-entity & paediatric registry modules (prostate, colorectal, melanoma, DKKR)"),
    ("modul_prostata", "Other-entity & paediatric registry modules (prostate, colorectal, melanoma, DKKR)"),
    ("modul_malignes_melanom", "Other-entity & paediatric registry modules (prostate, colorectal, melanoma, DKKR)"),
    ("gleason", "Other-entity & paediatric registry modules (prostate, colorectal, melanoma, DKKR)"),
    ("cabefallstanze", "Other-entity & paediatric registry modules (prostate, colorectal, melanoma, DKKR)"),
    ("hormonrezeptor", "Biomarker / receptor status"),
    ("8_biomarker", "Biomarker / receptor status"),
    ("menge_genetik", "Molecular tests / genomics"),
    ("nebenwirkung", "Adverse events / complications"),
    ("komplikation", "Adverse events / complications"),
    ("tumorkonferenz", "Tumour board / MDO"),
    (" tod ", "Follow-up, response, death & second tumour"),
    ("verlauf", "Follow-up, response, death & second tumour"),
    ("datum_n", "Follow-up, response, death & second tumour"),
    ("pathologie", "Pathology detail"),
    ("histologie", "Pathology detail"),
    ("modul_mamma", "Pathology detail"),
    ("tnm", "Diagnosis / staging detail (TNM, localisation, side)"),
    ("diagnose", "Diagnosis / staging detail (TNM, localisation, side)"),
    ("tumorzuordnung", "Diagnosis / staging detail (TNM, localisation, side)"),
    ("tumor_icd", "Diagnosis / staging detail (TNM, localisation, side)"),
    ("topographie", "Diagnosis / staging detail (TNM, localisation, side)"),
    ("morphologie", "Diagnosis / staging detail (TNM, localisation, side)"),
    ("residualstatus", "Diagnosis / staging detail (TNM, localisation, side)"),
    ("menge_fm", "Diagnosis / staging detail (TNM, localisation, side)"),
    ("weitere_klassifikation", "Diagnosis / staging detail (TNM, localisation, side)"),
    ("allgemein_icd", "Diagnosis / staging detail (TNM, localisation, side)"),
    ("5_disease", "Diagnosis / staging detail (TNM, localisation, side)"),
    (" op ", "Surgery / procedure detail (biopsy, implants, planning)"),
    ("operateur", "Surgery / procedure detail (biopsy, implants, planning)"),
    (" st ", "Treatment detail (drug, dose, cycles, fractions, technique)"),
    ("syst", "Treatment detail (drug, dose, cycles, fractions, technique)"),
    ("strahlendosis", "Treatment detail (drug, dose, cycles, fractions, technique)"),
    ("zielgebiet", "Treatment detail (drug, dose, cycles, fractions, technique)"),
    ("aktivitaets", "Treatment detail (drug, dose, cycles, fractions, technique)"),
    ("6_treatment", "Treatment detail (drug, dose, cycles, fractions, technique)"),
    ("name of the drug", "Treatment detail (drug, dose, cycles, fractions, technique)"),
    ("treatment setting", "Treatment detail (drug, dose, cycles, fractions, technique)"),
    ("7_environmental", "Patient history / risk factors"),
    ("2_patient", "Patient history / risk factors"),
    ("4_sample", "Genomics / biobank infrastructure"),
    ("3_sequence", "Genomics / biobank infrastructure"),
    ("1_submitter", "Administrative / identifiers / contact"),
    ("melder", "Administrative / identifiers / contact"),
    ("absender", "Administrative / identifiers / contact"),
    ("adresse", "Administrative / identifiers / contact"),
    ("versicherten", "Administrative / identifiers / contact"),
    ("ident_nummern", "Administrative / identifiers / contact"),
    ("stammdaten", "Administrative / identifiers / contact"),
    ("adressstring", "Administrative / identifiers / contact"),
    ("namenstring", "Administrative / identifiers / contact"),
    ("menge_zusatzitem", "Registry transport / XML structure"),
    ("modul_allgemein", "Registry transport / XML structure"),
    ("(root)", "Registry transport / XML structure"),
]
# whole-label overrides (lower-cased) for labels too short / too generic to key on
EXACT = {
    "patient": "Administrative / identifiers / contact",
    "patiënt": "Administrative / identifiers / contact",
    "patiã«nt": "Administrative / identifiers / contact",
    "naam patient": "Administrative / identifiers / contact",
    "patientidentificatienummer": "Administrative / identifiers / contact",
    "contactgegevens": "Administrative / identifiers / contact",
    "additioneleinformatie": "Administrative / identifiers / contact",
    "verlauf_lokaler_tumorstatus": "Follow-up, response, death & second tumour",
    "verlauf_tumorstatus_fernmetastasen": "Follow-up, response, death & second tumour",
    "verlauf_tumorstatus_lymphknoten": "Follow-up, response, death & second tumour",
    "verlauf.zweitttumordatum": "Follow-up, response, death & second tumour",
    "verlauf.zweitttumoricd": "Follow-up, response, death & second tumour",
    "systemischetherapie.firstlinemetastasiert": "Treatment detail (drug, dose, cycles, fractions, technique)",
    "operationsplanung.seite": "Surgery / procedure detail (biopsy, implants, planning)",
    "extranodale groei okd": "Pathology detail",
    "extranodale groei snb": "Pathology detail",
    "pt-diameter": "Pathology detail",
}
# ---------------------------------------------------------------------------
# Indication specificity (third attribute, field level)
#   generic       pan-cancer content — a hub gap in the strict sense
#   breast        breast-cancer-specific — expected to live in an extension
#   other-entity  prostate / colorectal / melanoma / paediatric registry items
# Keyword-based; the breast share is a lower bound.
# ---------------------------------------------------------------------------
BREAST_KW = [
    "mamma", "mammo", "borst", "brust", "breast", "dcis", "lobul", "ductal", "duktal",
    "her2", "oestrogen", "estrogen", "progesteron", "hormonrez", "receptor", "rezeptor",
    " er-", " pr-", ".er.", ".pr.", "biomarker.er", "biomarker.pr", "ki-67", "ki67", "bi-rads", "birads", " acr ", "acrdichte",
    "tepel", "mamille", "nipple", "okselklier", "axill", "menopau", "menarche",
    "hormonersatz", "huidsparend", "tepelsparend", "reconstruct", "rekonstru",
    "implantat", "implantaten", "prothese", "mammaprint", "oncotype", "nottingham",
    "cpseg", "senolog", "gynaekolog", "schwangerschaft", "zwanger", "borstvoedend",
    "b3", "microcalc", "mikrokalk", "calcificat", "fibroglandulair", "densiteit",
    "enhancement", "aankleuring", "intrammaire", "mariklier", "allredscore",
    "irsscore", "ovarial", "brca", "genexpress", "genprofiel", "uhrzeit",
    "mamillenabstand", "afstand tot de tepel", "sentinel", "schildwacht",
    "massa", "cyste", "asymmetrie", "laesie", "echografie", "mri", "elasticit",
    "vascularisatie", "geluidstransmissie", "projectierichting", "herdbefund",
    "achtergrondkleuring", "erblich", "familienanamnese", "familieanamnese",
]
OTHER_ENTITY_KW = [
    "prostat", "gleason", "psa", "rektum", "melanom", "darm", "kolorekt", "tumordicke",
    "ulzeration", "breslow", "dkkr", "gpoh", "stanze", "anokutan", "mesorektal",
]


def specificity(row) -> str:
    """'generic' | 'breast' | 'other-entity' for a load_source() row."""
    own = row["_own"] if isinstance(row, dict) else f" {row} ".lower()
    if any(k in own for k in OTHER_ENTITY_KW):
        return "other-entity"
    if any(k in own for k in BREAST_KW):
        return "breast"
    return "generic"


CARRIAGE = {m: c for m, c, _ in MODULES}
CARRIAGE[UNCLUSTERED[0]] = UNCLUSTERED[1]


def load_source(path: Path) -> list[dict]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    for r in rows:
        element = r.get("element", "")
        label = r.get("label", "")
        definition = r.get("definition", "")
        ctx = " ".join(r.get(k, "") for k in ("module", "domain", "type", "datatype"))
        r["_label"] = element or label or r.get("id", "")
        # own text: element path / label + definition, space-padded so that
        # " word " keywords can match whole values
        r["_own"] = f" {element} {label} {definition} ".lower()
        r["_ctx"] = f" {ctx} ".lower()
        # legacy: everything (kept for callers that still pass a string)
        r["_text"] = " ".join(str(v) for k, v in r.items() if not k.startswith("_")).lower()
    return rows


def _match(text: str, rules):
    for module, carriage, kws in rules:
        if any(k in text for k in kws):
            return module, carriage
    return None


def classify(row):
    """Return (module, carriage) for an unmapped source row.

    Accepts a row dict from load_source() (two-pass: own label first, parent
    context second) or, for backwards compatibility, a plain string (single
    pass over that string).
    """
    if isinstance(row, str):
        return _match(row, MODULES) or UNCLUSTERED
    leaf = row["_label"].rsplit(".", 1)[-1].lower()
    if row["_label"].lower() in EXACT:
        m = EXACT[row["_label"].lower()]
        return m, CARRIAGE[m]
    generic = leaf in GENERIC_LEAVES or len(leaf) <= 2
    if not generic:
        hit = _match(row["_own"], MODULES)
        if hit:
            return hit
    # generic leaf of a dotted path (Senologie): inherit the parent's cluster
    if generic and "." in row["_label"]:
        parent = row["_label"].rsplit(".", 1)[0].lower()
        hit = _match(f" {parent} ", MODULES)
        if hit:
            return hit
    # parent context (oBDS module / XSD type, B1MG domain)
    for key, module in CONTEXT:
        if key in row["_ctx"]:
            return module, CARRIAGE[module]
    # last resort for a generic leaf: its definition text
    if generic:
        return _match(row["_own"], MODULES) or (GENERIC_MODULE, CARRIAGE[GENERIC_MODULE])
    return UNCLUSTERED


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    mapped = set()
    for f in glob.glob(str(MAPPINGS / "*__to__eccdm.sssom.tsv")):
        for r in csv.DictReader(
                [l for l in open(f) if not l.startswith("#")], delimiter="\t"):
            if r.get("subject_id"):
                mapped.add(r["subject_id"])

    # module -> carriage, and module -> {source -> [labels]}
    carriage_of = {}
    by_module = defaultdict(lambda: defaultdict(list))
    totals = defaultdict(int)
    for src, path in SOURCES.items():
        for r in load_source(REPO / path):
            if r["id"] in mapped:
                continue
            module, carriage = classify(r)
            carriage_of[module] = carriage
            by_module[module][src].append(r["_label"])
            totals[src] += 1

    # order modules by carriage then size
    carr_rank = {"by-reference": 0, "extend-model": 1, "new-module": 2,
                 "out-of-scope": 3, "review": 4}
    mods = sorted(by_module, key=lambda m: (carr_rank[carriage_of[m]],
                                            -sum(len(v) for v in by_module[m].values())))

    lines = ["# Extension modules — inverse gaps (source-side, no ECCDM hub home)\n",
             "Generated by `scripts/inverse_gaps.py`. Every source element that maps",
             "to NO ECCDM hub element, clustered into candidate extension modules and",
             "classified by how ECCDM could carry it.\n",
             "- **by-reference** — needs an evidence hook + an Observation/Finding "
             "logical model on the hub; the finding then hangs off by reference.",
             "- **extend-model** — attribute-level detail of a model ECCDM already "
             "has (CancerStage, SystemicTreatment, Radiotherapy, Surgery, LastFollowUp).",
             "- **new-module** — needs a whole new hub model.",
             "- **out-of-scope** — administrative, registry transport, other-entity "
             "organ modules, genomics infrastructure: not clinical content ECCDM targets.",
             "- **review** — structural leaves whose context was lost in extraction.\n",
             f"Unmapped source elements: " +
             ", ".join(f"{s} {totals[s]}" for s in SOURCES) + ".\n"]

    for m in mods:
        n = sum(len(v) for v in by_module[m].values())
        lines.append(f"## {m}  ·  _{carriage_of[m]}_  ({n} fields)\n")
        for src in SOURCES:
            labs = by_module[m].get(src)
            if labs:
                ex = ", ".join(sorted(set(labs))[:8])
                more = f" … (+{len(set(labs)) - 8})" if len(set(labs)) > 8 else ""
                lines.append(f"- **{src}** ({len(labs)}): {ex}{more}")
        lines.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")

    # console summary
    print(f"Wrote {args.out}\n")
    print(f"{'module':38} {'carriage':16} {'fields':>6}")
    for m in mods:
        n = sum(len(v) for v in by_module[m].values())
        print(f"{m:38} {carriage_of[m]:16} {n:6}")
    print(f"\nTotal unmapped source elements: {sum(totals.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
