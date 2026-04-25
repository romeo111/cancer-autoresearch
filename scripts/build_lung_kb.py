"""Generate the full Lung-cancer KB vertical (NSCLC + SCLC).

DIS-NSCLC archetype: biomarker_driven. Molecular subtype + PD-L1 TPS
drive Algorithm decision_tree branches:
  - EGFR-mut: osimertinib (or 1G/2G TKI)
  - ALK-rearranged: alectinib / lorlatinib
  - ROS1: crizotinib / entrectinib
  - KRAS G12C: sotorasib / adagrasib
  - BRAF V600E: dabrafenib + trametinib
  - MET ex14: capmatinib / tepotinib
  - RET: selpercatinib
  - NTRK: larotrectinib / entrectinib
  - HER2 mut: trastuzumab deruxtecan (T-DXd)
  - Driver-negative + PD-L1 ≥50%: pembrolizumab mono
  - Driver-negative + PD-L1 1-49%: pembro + chemo
  - Driver-negative + PD-L1 <1%: pembro + chemo (or chemo alone)
  - Stage III unresectable: definitive CRT → durvalumab consolidation (PACIFIC)

DIS-SCLC archetype: stage_driven (limited / extensive). Etoposide-platinum
backbone; +atezolizumab (extensive, IMpower133) or +durvalumab (extensive,
CASPIAN) or +RT (limited, CONVERT).

Per CHARTER §8.3: extraction from NCCN/ESMO. Two-reviewer merge per §6.1.
Per user 2026-04-26: efficacy > UA-registration. Best-evidence drugs
included regardless of NSZU status.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
KB = REPO_ROOT / "knowledge_base" / "hosted" / "content"


def write(rel: str, body: str) -> None:
    target = KB / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    print(f"wrote {rel}")


# ── Drug template (compact) ────────────────────────────────────────────


DRUG_T = """\
id: {id}
names:
  preferred: "{preferred}"
  ukrainian: "{ukrainian}"
  english: "{preferred}"
  brand_names: {brands}
atc_code: {atc}
rxnorm_id: null
drug_class: "{drug_class}"
mechanism: >
  {mechanism}

regulatory_status:
  fda: {{approved: {fda}}}
  ema: {{approved: {ema}}}
  ukraine_registration:
    registered: {ua_registered}
    reimbursed_nszu: {ua_reimbursed}
    last_verified: null
    notes: "{ua_notes}"

typical_dosing: >
  {dosing}

key_toxicities:
{toxicities}

sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-METASTATIC-2024]
last_reviewed: null
notes: >
  {notes}
"""


def _drug(id_, preferred, ukrainian, brands, atc, drug_class, mechanism,
          fda, ema, ua_reg, ua_reim, ua_notes, dosing, toxicities, notes):
    bl = "[" + ", ".join(f'"{b}"' for b in brands) + "]" if brands else "[]"
    tx = "\n".join(f"  - {t}" for t in toxicities) or "  - (none specific)"
    return DRUG_T.format(
        id=id_, preferred=preferred, ukrainian=ukrainian, brands=bl,
        atc=atc, drug_class=drug_class, mechanism=mechanism,
        fda=str(fda).lower(), ema=str(ema).lower(),
        ua_registered=str(ua_reg).lower(), ua_reimbursed=str(ua_reim).lower(),
        ua_notes=ua_notes.replace('"', '\\"'), dosing=dosing,
        toxicities=tx, notes=notes,
    )


# ── 1. Disease (NSCLC + SCLC) ──────────────────────────────────────────


DISEASE_NSCLC = """\
id: DIS-NSCLC
names:
  preferred: "Non-small cell lung cancer"
  ukrainian: "Недрібноклітинний рак легені"
  english: "Non-small cell lung cancer"
  synonyms: ["NSCLC", "НДРЛ"]

codes:
  icd_o_3_morphology: "8046/3"
  icd_o_3_topography: ["C34.9"]
  icd_10: "C34"
  who_classification: "Non-small cell lung carcinoma — adenocarcinoma / squamous / large cell (WHO 5th 2021)"

archetype: biomarker_driven
lineage: solid_tumor_lung_nsclc

# Molecular subtypes — drive Algorithm decision_tree
molecular_subtypes:
  - id: EGFR_MUT
    label: "EGFR-mutant (exon 19 deletion / L858R / uncommon)"
    label_ua: "EGFR-мутантний"
    actionable_drugs: ["osimertinib (1L preferred)", "erlotinib", "gefitinib", "afatinib", "dacomitinib"]
  - id: ALK_REARRANGED
    label: "ALK-rearranged (EML4-ALK and variants)"
    label_ua: "ALK-перебудований"
    actionable_drugs: ["alectinib (1L preferred)", "brigatinib", "lorlatinib", "crizotinib"]
  - id: ROS1
    label: "ROS1 fusion"
    label_ua: "ROS1-фузія"
    actionable_drugs: ["entrectinib", "crizotinib", "lorlatinib", "repotrectinib"]
  - id: KRAS_G12C
    label: "KRAS G12C mutation"
    label_ua: "KRAS G12C мутація"
    actionable_drugs: ["sotorasib", "adagrasib"]
  - id: BRAF_V600E
    label: "BRAF V600E mutation"
    label_ua: "BRAF V600E мутація"
    actionable_drugs: ["dabrafenib + trametinib"]
  - id: MET_EX14
    label: "MET exon 14 skipping mutation"
    label_ua: "MET exon 14 skipping"
    actionable_drugs: ["capmatinib", "tepotinib"]
  - id: RET_FUSION
    label: "RET fusion"
    label_ua: "RET-фузія"
    actionable_drugs: ["selpercatinib", "pralsetinib"]
  - id: NTRK_FUSION
    label: "NTRK fusion"
    label_ua: "NTRK-фузія"
    actionable_drugs: ["larotrectinib", "entrectinib"]
  - id: HER2_MUT
    label: "HER2 (ERBB2) mutation"
    label_ua: "HER2 (ERBB2) мутація"
    actionable_drugs: ["trastuzumab deruxtecan (T-DXd)"]
  - id: DRIVER_NEGATIVE
    label: "No actionable driver — PD-L1 / immunotherapy ± chemo path"
    label_ua: "Без таргет-драйвера — PD-L1 / імунотерапія ± хіміо"
    actionable_drugs: ["pembrolizumab ± chemo", "atezolizumab + chemo", "cemiplimab", "nivolumab + ipilimumab + chemo"]

# Stage strata
stage_strata:
  - id: STAGE_I_II_RESECTABLE
    label: "Stage I-II resectable"
    definition: "Localized; surgical resection ± adjuvant chemo / osimertinib (EGFR+) / atezolizumab (PD-L1+)"
  - id: STAGE_III_UNRESECTABLE
    label: "Stage III locally advanced unresectable"
    definition: "Concurrent chemoradiation → durvalumab consolidation (PACIFIC)"
  - id: STAGE_IV_METASTATIC
    label: "Stage IV metastatic"
    definition: "Driver-targeted therapy or immunotherapy ± chemo per molecular + PD-L1 status"

# PD-L1 TPS strata (relevant only for driver-negative)
pdl1_tps_strata:
  - id: TPS_HIGH
    label: "PD-L1 TPS ≥50% — pembrolizumab monotherapy candidate"
  - id: TPS_INTERMEDIATE
    label: "PD-L1 TPS 1-49% — pembro + chemo"
  - id: TPS_NEGATIVE
    label: "PD-L1 TPS <1% — pembro + chemo OR chemo alone (immunotherapy benefit smaller)"

prognostic_frameworks:
  - id: AJCC-8TH-LUNG
    label: "AJCC 8th edition TNM staging"
    used_for: "Anatomic stage stratification"

etiological_factors:
  - "Tobacco smoking — dominant risk for squamous + most adenocarcinoma"
  - "Radon, asbestos, air pollution — environmental contributors"
  - "Driver-mutant adenocarcinoma in never-smokers / light smokers (~80% of EGFR-mut, ALK, ROS1 patients are never-smokers)"

related_diseases:
  - "DIS-SCLC"
  - "DIS-MESOTHELIOMA"

epidemiology:
  context: >
    Most common cancer cause of death globally. ~85% of all lung cancers
    are NSCLC; remaining ~15% SCLC. Adenocarcinoma > squamous in incidence
    in modern era. 5-year OS varies by stage: I ~80%, IV ~10% — but
    targeted therapy in driver-mutant subtypes shifts metastatic OS to
    ≥3-5 years for EGFR/ALK. UA practice gap: NGS-panel availability
    + funding for expensive targeted TKIs.

sources:
  - SRC-NCCN-NSCLC-2025
  - SRC-ESMO-NSCLC-METASTATIC-2024
  - SRC-ESMO-NSCLC-EARLY-2024

last_reviewed: null
reviewers: []
notes: >
  archetype: biomarker_driven — molecular profiling the dominant
  branch point. Universal NGS panel (DNA + RNA fusion) recommended at
  metastatic diagnosis. Reflex PD-L1 IHC standard. Schema gaps absorbed
  by extra="allow" Base config: molecular_subtypes, stage_strata,
  pdl1_tps_strata. Pending unification with PROPOSAL §17/§18.
"""


DISEASE_SCLC = """\
id: DIS-SCLC
names:
  preferred: "Small cell lung cancer"
  ukrainian: "Дрібноклітинний рак легені"
  english: "Small cell lung cancer"
  synonyms: ["SCLC", "ДРЛ"]

codes:
  icd_o_3_morphology: "8041/3"
  icd_o_3_topography: ["C34.9"]
  icd_10: "C34"
  who_classification: "Small cell lung carcinoma — neuroendocrine tumor (WHO 5th 2021)"

archetype: stage_driven
lineage: solid_tumor_lung_sclc

stage_strata:
  - id: LIMITED
    label: "Limited-stage SCLC"
    label_ua: "Обмежена стадія SCLC"
    definition: "Disease confined to one hemithorax, encompassable in one tolerable RT field; ~30% of SCLC at presentation"
  - id: EXTENSIVE
    label: "Extensive-stage SCLC"
    label_ua: "Поширена стадія SCLC"
    definition: "Disease beyond one hemithorax (contralateral lung, distant metastases); ~70% at presentation"

prognostic_frameworks:
  - id: VALG
    label: "VALG (Veterans Administration Lung Group) staging — limited vs extensive"
    used_for: "Standard binary SCLC staging — drives treatment choice"
  - id: AJCC-8TH-LUNG
    label: "AJCC 8th edition TNM (recently extended to SCLC)"
    used_for: "Refined T/N/M stratification within VALG strata"

etiological_factors:
  - "Tobacco smoking — overwhelming dominant risk (>95% of SCLC); rare in never-smokers"
  - "Neuroendocrine differentiation — rapid proliferation, paraneoplastic syndromes (SIADH, Cushing's, Lambert-Eaton, autoimmune limbic encephalitis)"

related_diseases:
  - "DIS-NSCLC"
  - "DIS-CARCINOID-LUNG"

epidemiology:
  context: >
    ~15% of all lung cancers. Median age ~70. Aggressive natural history
    — extensive-stage median OS historically ~10 months, now 13-15 months
    with EP + atezolizumab/durvalumab (IMpower133, CASPIAN). Limited-stage
    median OS 25-30 months with EP + concurrent RT. Late-onset PCI
    (prophylactic cranial irradiation) controversial in extensive-stage
    after MRI-surveillance era.

sources:
  - SRC-NCCN-SCLC-2025
  - SRC-ESMO-SCLC-2021

last_reviewed: null
reviewers: []
notes: >
  archetype: stage_driven — limited vs extensive is the dominant fork.
  Modern era: chemoimmunotherapy combinations standard for extensive;
  chemo + concurrent RT for limited. Targeted/biomarker-driven options
  (e.g., DLL3-targeted tarlatamab for extensive 2L+) emerging but not
  yet 1L standard.
"""


# ── 2. Sources (4 new) ─────────────────────────────────────────────────


SOURCES: dict[str, str] = {}


def _source(id_, title, version, url, relates, notes_extra=""):
    return f"""\
id: {id_}
source_type: guideline
title: {title}
version: '{version}'
authors:
  - {'NCCN' if 'NCCN' in id_ else 'ESMO'} Guidelines Committee
journal: {'null' if 'NCCN' in id_ else 'Annals of Oncology'}
doi: null
url: {url}
access_level: {'registration_required' if 'NCCN' in id_ else 'open_access'}
currency_status: current
superseded_by: null
current_as_of: '{version[:4]}-10-01'
evidence_tier: 1
hosting_mode: referenced
hosting_justification: null
ingestion:
  method: none
  client: null
  endpoint: null
  rate_limit: null
cache_policy:
  enabled: false
  ttl_hours: null
  scope: null
license:
  name: {'NCCN — clinician-only redistribution prohibited' if 'NCCN' in id_ else 'CC-BY-NC-ND 4.0 (typical for ESMO / Annals of Oncology)'}
  url: {'https://www.nccn.org/permissions' if 'NCCN' in id_ else 'https://creativecommons.org/licenses/by-nc-nd/4.0/'}
  spdx_id: {'null' if 'NCCN' in id_ else 'CC-BY-NC-ND-4.0'}
attribution:
  required: true
  text: '{title}, v{version}'
commercial_use_allowed: false
redistribution_allowed: false
modifications_allowed: false
sharealike_required: false
known_restrictions:
  - 'Quote-paraphrase model; no derivative redistribution'
legal_review:
  status: pending
  reviewer: null
  date: null
  notes: Same posture as SRC-NCCN-PROSTATE-2025 / SRC-ESMO-DLBCL-2024
relates_to_diseases:
{relates}
last_verified: null
notes: >
  {notes_extra}
pages_count: 250
references_count: 600
corpus_role: primary_guideline
"""


SOURCES["src_nccn_nsclc_2025.yaml"] = _source(
    "SRC-NCCN-NSCLC-2025",
    "NCCN Clinical Practice Guidelines — Non-Small Cell Lung Cancer",
    "2025.v8",
    "https://www.nccn.org/professionals/physician_gls/pdf/nscl.pdf",
    "  - DIS-NSCLC",
    "Primary international guideline for NSCLC. Codifies universal NGS testing for advanced disease, driver-mutation 1L therapy hierarchies (FLAURA: osimertinib > 1G TKI; ALEX: alectinib > crizotinib), PACIFIC-style durva consolidation, KEYNOTE-024 / KEYNOTE-189 / KEYNOTE-407 PD-L1 + chemo strategies."
)
SOURCES["src_esmo_nsclc_metastatic_2024.yaml"] = _source(
    "SRC-ESMO-NSCLC-METASTATIC-2024",
    "ESMO Clinical Practice Guideline on Metastatic Non-Small Cell Lung Cancer",
    "2024",
    "https://www.esmo.org/guidelines/guidelines-by-topic/lung-cancer/metastatic-nsclc",
    "  - DIS-NSCLC",
    "Driver-mutation hierarchy + 1L sequencing for metastatic NSCLC. Detailed osimertinib first-line (FLAURA + FLAURA2 osi+chemo combination), alectinib first-line ALK (ALEX), KRAS G12C 2L+ (CodeBreaK 100/200), BRAF V600E doublet (dabrafenib + trametinib), MET ex14 (capmatinib + tepotinib), RET (selpercatinib), NTRK (larotrectinib + entrectinib), HER2-mut T-DXd (DESTINY-Lung01/02). Driver-negative: pembrolizumab mono PD-L1≥50% (KEYNOTE-024), pembro+chemo PD-L1<50% (KEYNOTE-189/407), atezolizumab combinations."
)
SOURCES["src_esmo_nsclc_early_2024.yaml"] = _source(
    "SRC-ESMO-NSCLC-EARLY-2024",
    "ESMO Clinical Practice Guideline on Early NSCLC + Stage III",
    "2024",
    "https://www.esmo.org/guidelines/guidelines-by-topic/lung-cancer/early-and-locally-advanced-nsclc",
    "  - DIS-NSCLC",
    "Resectable I-II + locally-advanced III. Adjuvant osimertinib (ADAURA) for EGFR-mut stage IB-IIIA resected. Atezolizumab adjuvant (IMpower010) for PD-L1≥1% stage II-IIIA resected. PACIFIC durvalumab consolidation post-CRT for stage III unresectable. Neoadjuvant chemo+ICI (CheckMate-816 nivolumab+chemo) for resectable stage II-IIIA."
)
SOURCES["src_nccn_sclc_2025.yaml"] = _source(
    "SRC-NCCN-SCLC-2025",
    "NCCN Clinical Practice Guidelines — Small Cell Lung Cancer",
    "2025.v3",
    "https://www.nccn.org/professionals/physician_gls/pdf/sclc.pdf",
    "  - DIS-SCLC",
    "Limited-stage: EP + concurrent RT (CONVERT once-daily 60 Gy or twice-daily 45 Gy). Extensive-stage: EP + atezolizumab (IMpower133) or EP + durvalumab (CASPIAN) — durva preferred per ESMO; atezo per NCCN. PCI consideration for limited-stage CR/PR; controversial for extensive-stage in MRI-surveillance era. 2L+: lurbinectedin, topotecan, irinotecan, tarlatamab (DLL3-targeted bispecific)."
)
SOURCES["src_esmo_sclc_2021.yaml"] = _source(
    "SRC-ESMO-SCLC-2021",
    "ESMO Clinical Practice Guideline on Small Cell Lung Cancer",
    "2021",
    "https://www.esmo.org/guidelines/guidelines-by-topic/lung-cancer/small-cell-lung-cancer",
    "  - DIS-SCLC",
    "Pre-IMpower133 / CASPIAN baseline. Updated supplementary recommendations integrate ICI combinations for extensive-stage. Note: 2024 ESMO update under review."
)


# ── 3. Drugs (~17 new TKIs) ─────────────────────────────────────────────


DRUGS: list[tuple[str, str]] = [
    ("osimertinib.yaml", _drug(
        "DRUG-OSIMERTINIB", "Osimertinib", "Осимертиніб",
        ["Tagrisso"], "L01EB04",
        "3rd-generation EGFR TKI (T790M-active)",
        "Irreversible covalent EGFR-TKI selective for activating mutations and T790M resistance mutation. Excellent CNS penetration. 1L preferred for EGFR-mut metastatic per FLAURA + FLAURA2; adjuvant for stage IB-IIIA EGFR-mut resected per ADAURA.",
        True, True, True, False,
        "Registered; reimbursement under negotiation. Out-of-pocket for most patients in Ukraine; major access barrier for EGFR-mut population. Clinical-review queue priority.",
        "1L: 80 mg PO once daily. Continue until progression. ADAURA adjuvant: 80 mg PO daily x 3 years.",
        ["Diarrhea (~50%)", "Rash (~30%, milder than 1G TKIs)", "Paronychia",
         "Cardiac (QT prolongation, LVEF decline; ECG + echo monitoring)",
         "Pneumonitis (~3-5%, can be fatal — CT chest on respiratory symptoms)",
         "Stomatitis"],
        "FLAURA: osimertinib superior to 1G TKIs in 1L EGFR-mut metastatic. FLAURA2: osimertinib + chemo further extends PFS. ADAURA: adjuvant 3-year osi reduces recurrence by 80% vs placebo in resected EGFR-mut stage IB-IIIA.",
    )),
    ("erlotinib.yaml", _drug(
        "DRUG-ERLOTINIB", "Erlotinib", "Ерлотиніб",
        ["Tarceva"], "L01EB02",
        "1st-generation EGFR TKI (reversible)",
        "Reversible EGFR-TKI. Pre-T790M era 1L standard; now 2L+ or alternate when osimertinib unavailable.",
        True, True, True, True,
        "Generic; reimbursed.",
        "150 mg PO once daily on empty stomach.",
        ["Rash / acneiform eruption (~75%)", "Diarrhea", "Fatigue",
         "Hepatic transaminase elevations", "ILD (~1-2%)"],
        "Largely supplanted by osimertinib in 1L. 2L+ option when osi-resistance pathway not amenable to next-line targeted; rare in modern era.",
    )),
    ("gefitinib.yaml", _drug(
        "DRUG-GEFITINIB", "Gefitinib", "Гефітиніб",
        ["Iressa"], "L01EB01",
        "1st-generation EGFR TKI (reversible)",
        "Reversible EGFR-TKI similar to erlotinib. Equivalent efficacy in clinical use.",
        True, True, True, True,
        "Generic; reimbursed.",
        "250 mg PO once daily.",
        ["Same class profile as erlotinib (rash, diarrhea, fatigue)"],
        "Interchangeable with erlotinib. Also supplanted by osimertinib in 1L.",
    )),
    ("afatinib.yaml", _drug(
        "DRUG-AFATINIB", "Afatinib", "Афатиніб",
        ["Gilotrif", "Giotrif"], "L01EB03",
        "2nd-generation EGFR/HER2 TKI (irreversible)",
        "Irreversible pan-HER (EGFR / HER2 / HER4) TKI. More toxic than 1G TKIs but covers some uncommon EGFR mutations (G719X, L861Q, S768I). LUX-Lung 7 / 8: superior PFS vs gefitinib / erlotinib in selected populations.",
        True, True, True, False,
        "Registered; reimbursement variable.",
        "40 mg PO once daily on empty stomach. Reduce to 30 mg if intolerable diarrhea.",
        ["Diarrhea (~95%)", "Rash", "Stomatitis", "Paronychia"],
        "Niche use for uncommon EGFR mutations not covered by osimertinib. Rarely first-line in modern era.",
    )),
    ("dacomitinib.yaml", _drug(
        "DRUG-DACOMITINIB", "Dacomitinib", "Дакомітініб",
        ["Vizimpro"], "L01EB07",
        "2nd-generation EGFR TKI (irreversible)",
        "Irreversible pan-HER TKI. ARCHER 1050: superior PFS + OS vs gefitinib in 1L EGFR-mut metastatic. Pre-osimertinib alternative.",
        True, True, False, False,
        "Not registered in Ukraine. Off-label access.",
        "45 mg PO once daily.",
        ["Rash", "Diarrhea", "Paronychia", "More AEs than 1G/3G TKIs"],
        "Niche role; osimertinib is the modern 1L. Listed for completeness.",
    )),
    ("alectinib.yaml", _drug(
        "DRUG-ALECTINIB", "Alectinib", "Алектиніб",
        ["Alecensa"], "L01ED03",
        "2nd-generation ALK inhibitor (CNS-penetrant)",
        "ALK + RET inhibitor with excellent CNS penetration. ALEX: superior PFS + intracranial response vs crizotinib in 1L ALK-rearranged metastatic. Adjuvant ALINA: 3-year DFS benefit in resected ALK+ stage IB-IIIA.",
        True, True, True, False,
        "Registered; reimbursement under negotiation; out-of-pocket for many. UA-access major barrier for ALK+ population.",
        "600 mg PO BID with food. Adjuvant ALINA: 600 mg BID x 2 years.",
        ["Anemia", "Myalgia / CK elevation", "Fatigue",
         "Photosensitivity rash", "Bradycardia",
         "Hepatotoxicity"],
        "Workhorse 1L ALK inhibitor. CNS efficacy critical (high CNS-met rate in ALK+).",
    )),
    ("brigatinib.yaml", _drug(
        "DRUG-BRIGATINIB", "Brigatinib", "Бригатиніб",
        ["Alunbrig"], "L01ED04",
        "2nd-generation ALK inhibitor",
        "ALK / ROS1 inhibitor with broad-spectrum activity vs ALK resistance mutations. ALTA-1L: superior PFS vs crizotinib 1L.",
        True, True, False, False,
        "Not registered in Ukraine. Off-label access.",
        "180 mg PO once daily after 7-day lead-in at 90 mg.",
        ["Pulmonary AEs (early-onset cough, dyspnea — hence lead-in dosing)",
         "Hypertension", "GI", "CK elevation"],
        "Alternative to alectinib 1L with similar efficacy; choice often based on AE profile preference.",
    )),
    ("lorlatinib.yaml", _drug(
        "DRUG-LORLATINIB", "Lorlatinib", "Лорлатініб",
        ["Lorbrena"], "L01ED05",
        "3rd-generation ALK / ROS1 inhibitor",
        "Macrocyclic ALK/ROS1 TKI with activity vs nearly all ALK resistance mutations + excellent CNS penetration. CROWN: superior PFS vs crizotinib 1L (3-year PFS rate 64% lorlatinib vs 19% crizotinib).",
        True, True, False, False,
        "Not registered in Ukraine. Off-label access; major barrier.",
        "100 mg PO once daily.",
        ["Hypercholesterolemia / hypertriglyceridemia (>90% — statin management)",
         "Edema", "Cognitive AEs (memory, mood, confusion — class warning)",
         "Peripheral neuropathy", "Weight gain"],
        "CROWN trial: most active ALK TKI to date, with 3-year PFS exceeding any prior ALK 1L. Cognitive AE profile distinct — careful patient selection. Effective for post-alectinib resistance.",
    )),
    ("crizotinib.yaml", _drug(
        "DRUG-CRIZOTINIB", "Crizotinib", "Кризотиніб",
        ["Xalkori"], "L01ED01",
        "1st-generation ALK / ROS1 / MET inhibitor",
        "Multi-target TKI active in ALK, ROS1, and MET-driven NSCLC. Largely supplanted by alectinib/lorlatinib for ALK and entrectinib for ROS1, but retains role in ROS1+ NSCLC where access to newer agents limited.",
        True, True, True, True,
        "Registered; reimbursed for ALK-rearranged metastatic NSCLC.",
        "250 mg PO BID.",
        ["Visual disturbances (~60%)", "Edema", "Diarrhea", "Nausea",
         "Hepatotoxicity", "QT prolongation", "Pneumonitis (rare)"],
        "ROS1-positive NSCLC standard 1L when entrectinib unavailable. Largely 2L+ for ALK now.",
    )),
    ("entrectinib.yaml", _drug(
        "DRUG-ENTRECTINIB", "Entrectinib", "Ентректініб",
        ["Rozlytrek"], "L01EX14",
        "ROS1 / NTRK / ALK TKI (CNS-penetrant)",
        "Multi-kinase inhibitor (TRKA/B/C / ROS1 / ALK) with high CNS penetration. Tumor-agnostic NTRK-fusion indication; 1L preferred for ROS1+ NSCLC per ESMO.",
        True, True, False, False,
        "Not registered in Ukraine. Off-label access.",
        "600 mg PO once daily.",
        ["Dysgeusia", "Constipation", "Fatigue",
         "Cognitive / mood (TRK class)", "Weight gain", "Hepatic"],
        "STARTRK-2: tumor-agnostic NTRK + ROS1 efficacy. Larotrectinib alternative for NTRK-only.",
    )),
    ("sotorasib.yaml", _drug(
        "DRUG-SOTORASIB", "Sotorasib", "Сотерасіб",
        ["Lumakras"], "L01XX73",
        "KRAS G12C-selective covalent inhibitor",
        "First-in-class covalent inhibitor of KRAS G12C — locks the protein in its inactive GDP-bound state. CodeBreaK 100: ORR ~37% in pretreated KRAS G12C+ NSCLC.",
        True, True, False, False,
        "Not registered in Ukraine. Off-label access; major barrier.",
        "960 mg PO once daily.",
        ["Diarrhea", "Hepatotoxicity (~25% transaminase elevation)",
         "Nausea", "Fatigue", "Pneumonitis (rare)"],
        "CodeBreaK 200 vs docetaxel in 2L: PFS benefit, OS not significant. Approved 2L+ for KRAS G12C-mutant NSCLC.",
    )),
    ("adagrasib.yaml", _drug(
        "DRUG-ADAGRASIB", "Adagrasib", "Адаграсіб",
        ["Krazati"], "L01XX76",
        "KRAS G12C inhibitor (CNS-penetrant)",
        "KRAS G12C-selective covalent inhibitor with greater CNS penetration than sotorasib. KRYSTAL-1: ORR ~43% in pretreated KRAS G12C+ NSCLC, intracranial response ~33%.",
        True, True, False, False,
        "Not registered in Ukraine. Off-label access.",
        "600 mg PO BID.",
        ["Diarrhea, nausea, vomiting (high)",
         "QT prolongation",
         "Hepatotoxicity",
         "Renal impairment"],
        "Better CNS profile than sotorasib makes it preferred for brain-met-positive KRAS G12C+ disease.",
    )),
    ("dabrafenib.yaml", _drug(
        "DRUG-DABRAFENIB", "Dabrafenib", "Дабрафеніб",
        ["Tafinlar"], "L01EC02",
        "BRAF inhibitor",
        "Selective BRAF V600E/K inhibitor. Always combined with trametinib (MEKi) to prevent paradoxical RAF activation in BRAF-WT cells and improve efficacy.",
        True, True, True, False,
        "Registered; reimbursement varies. Used across BRAF V600E NSCLC, melanoma, ATC, CRC (with cetuximab).",
        "150 mg PO BID + trametinib 2 mg PO daily.",
        ["Pyrexia (~60% — class effect)", "Rash", "Fatigue",
         "Cutaneous SCC (paradoxical activation; less with MEKi combo)",
         "Hyperglycemia", "QT prolongation"],
        "BRAF V600E NSCLC 1L+. Pyrexia management: hold + restart at lower dose; antipyretics. Combination essential.",
    )),
    ("trametinib.yaml", _drug(
        "DRUG-TRAMETINIB", "Trametinib", "Траметиніб",
        ["Mekinist"], "L01EE01",
        "MEK1/2 inhibitor",
        "Selective MEK inhibitor used in combination with dabrafenib. Reduces resistance + skin toxicity vs BRAFi alone.",
        True, True, True, False,
        "Registered; reimbursement varies.",
        "2 mg PO once daily + dabrafenib 150 mg BID.",
        ["Cardiomyopathy / LVEF decline (echo monitoring)",
         "Retinal events (CSR-like)",
         "Hypertension", "Rash", "Diarrhea"],
        "Always combined with dabrafenib for BRAF V600E NSCLC, melanoma, ATC. Cardiac monitoring critical.",
    )),
    ("capmatinib.yaml", _drug(
        "DRUG-CAPMATINIB", "Capmatinib", "Капматініб",
        ["Tabrecta"], "L01EX17",
        "MET-selective TKI",
        "Selective inhibitor of MET (c-MET) tyrosine kinase. GEOMETRY mono-1: ORR ~68% in 1L MET ex14-mutant NSCLC.",
        True, True, False, False,
        "Not registered in Ukraine. Off-label access.",
        "400 mg PO BID with food.",
        ["Peripheral edema", "Nausea", "Fatigue",
         "Hepatotoxicity", "Pneumonitis (rare)"],
        "Indicated for MET ex14 skipping mutation NSCLC. Tepotinib alternative.",
    )),
    ("tepotinib.yaml", _drug(
        "DRUG-TEPOTINIB", "Tepotinib", "Тепотініб",
        ["Tepmetko"], "L01EX21",
        "MET-selective TKI",
        "Selective MET inhibitor with similar efficacy profile to capmatinib. VISION trial: ORR ~46% in 1L MET ex14+ NSCLC.",
        True, True, False, False,
        "Not registered in Ukraine. Off-label access.",
        "450 mg PO once daily.",
        ["Peripheral edema (~70%)", "Nausea", "Fatigue",
         "Hepatic enzyme elevation"],
        "Once-daily alternative to capmatinib BID. Edema dominant AE.",
    )),
    ("selpercatinib.yaml", _drug(
        "DRUG-SELPERCATINIB", "Selpercatinib", "Селперкатиніб",
        ["Retevmo"], "L01EX22",
        "RET-selective TKI",
        "Highly selective RET inhibitor. LIBRETTO-001: ORR ~85% in 1L RET-fusion+ NSCLC. Tumor-agnostic for RET-fusion / RET-mutant cancers (also MTC, papillary thyroid).",
        True, True, False, False,
        "Not registered in Ukraine. Off-label access; major barrier.",
        "160 mg PO BID (≥50 kg) or 120 mg BID (<50 kg) with food.",
        ["Hypertension (~40%)", "Hepatotoxicity",
         "QT prolongation", "Hemorrhage", "Hypersensitivity"],
        "RET-fusion NSCLC 1L+. High response rate transformative for this rare driver.",
    )),
    ("larotrectinib.yaml", _drug(
        "DRUG-LAROTRECTINIB", "Larotrectinib", "Ларотректініб",
        ["Vitrakvi"], "L01EX12",
        "TRK-selective inhibitor",
        "Tumor-agnostic NTRK-fusion-targeted TKI. Highly active across NTRK1/2/3-fusion cancers including NSCLC. Not active in NTRK-WT.",
        True, True, False, False,
        "Not registered in Ukraine. Off-label / international referral.",
        "100 mg PO BID.",
        ["Fatigue", "Dizziness / cognitive AEs (TRK class)",
         "Hepatic enzyme elevation",
         "Withdrawal pain (paradoxical pain on dose interruption)"],
        "Cross-disease tumor-agnostic indication. NTRK testing universal in NSCLC NGS panels.",
    )),
]


# ── 4. Biomarkers (5 new lung-relevant — most exist) ───────────────────


BIOMARKERS: list[tuple[str, str]] = [
    ("bio_egfr_mutation.yaml", """\
id: BIO-EGFR-MUTATION
names:
  preferred: "EGFR mutation status (NSCLC actionable)"
  ukrainian: "Статус мутацій EGFR (NSCLC actionable)"
codes:
  loinc: null

biomarker_type: mutation
mutation_details:
  gene: "EGFR"
  hotspots: ["exon 19 deletion (Δ746-750 most common)", "L858R", "L861Q", "G719X", "S768I", "T790M (resistance)", "exon 20 insertion (variable)"]
  type: "activating + resistance"
  functional_impact: "Constitutive EGFR signaling activation; T790M confers gefitinib/erlotinib resistance"

measurement:
  method: "Tumor-tissue NGS panel OR ctDNA NGS OR PCR (cobas EGFR Mutation Test)"
  sensitivity_requirement: "VAF detection threshold ≥1% for ctDNA; tissue more sensitive"

interpretation_notes: >
  ~10-15% of Western adenocarcinoma; 30-50% in East Asian populations.
  Common (exon 19 del + L858R) ~85-90% of EGFR-mut cases — best response
  to osimertinib. Uncommon mutations: variable response; afatinib /
  dacomitinib may be preferred for some. T790M resistance: osimertinib
  active. Exon 20 ins: poor response to standard EGFR TKIs; amivantamab
  + chemo or mobocertinib (where available).

related_biomarkers: []

last_reviewed: null
notes: >
  NCCN 2025 mandates universal EGFR testing for advanced non-squamous NSCLC.
"""),
    ("bio_alk_fusion.yaml", """\
id: BIO-ALK-FUSION
names:
  preferred: "ALK rearrangement / fusion"
  ukrainian: "Перебудова / фузія ALK"
codes:
  loinc: null

biomarker_type: fusion
mutation_details:
  gene: "ALK"
  partners: ["EML4 (most common)", "KIF5B", "TFG", "KLC1", "STRN", "and others"]
  type: "chromosomal rearrangement (typically inversion at 2p21-23)"
  functional_impact: "Constitutive ALK kinase activation"

measurement:
  method: "RNA-based NGS (preferred for fusion sensitivity) OR FISH OR IHC (D5F3 antibody)"
  sensitivity_requirement: "RNA-NGS captures fusion partners; FISH break-apart probe detects rearrangements"

interpretation_notes: >
  ~5% of NSCLC adenocarcinoma; enriched in never-smokers and younger
  patients. ALEX / CROWN: alectinib / lorlatinib superior to crizotinib
  1L. ALINA: 2-year alectinib adjuvant after resection.

related_biomarkers: []

last_reviewed: null
notes: >
  IHC screen → confirmatory FISH or NGS. Modern NGS panels detect ALK
  fusions directly.
"""),
    ("bio_ros1_fusion.yaml", """\
id: BIO-ROS1-FUSION
names:
  preferred: "ROS1 fusion"
  ukrainian: "Фузія ROS1"
codes:
  loinc: null

biomarker_type: fusion
mutation_details:
  gene: "ROS1"
  partners: ["CD74 (most common)", "EZR", "SLC34A2", "SDC4", "and others"]
  type: "chromosomal rearrangement"
  functional_impact: "Constitutive ROS1 kinase activation"

measurement:
  method: "RNA-based NGS OR FISH OR IHC screen"
  sensitivity_requirement: "Same as ALK"

interpretation_notes: >
  ~1-2% of NSCLC adenocarcinoma; never-smoker enriched. Crizotinib /
  entrectinib / lorlatinib effective; entrectinib preferred for CNS-active
  brain metastases.

related_biomarkers: []

last_reviewed: null
notes: >
  Often co-tested with ALK on same NGS panel.
"""),
    ("bio_kras_g12c.yaml", """\
id: BIO-KRAS-G12C
names:
  preferred: "KRAS G12C mutation"
  ukrainian: "KRAS G12C мутація"
codes:
  loinc: null

biomarker_type: mutation
mutation_details:
  gene: "KRAS"
  hotspots: ["G12C (codon 12, glycine→cysteine)"]
  type: "activating missense"
  functional_impact: "GTP-bound active KRAS; cysteine residue is the covalent target of sotorasib/adagrasib"

measurement:
  method: "Tumor-tissue NGS OR ctDNA NGS OR allele-specific PCR"
  sensitivity_requirement: "Standard NGS"

interpretation_notes: >
  ~13% of NSCLC adenocarcinoma; smoking-associated. Sotorasib + adagrasib
  available for 2L+. KRAS WT or non-G12C variants not actionable with
  current G12C inhibitors.

related_biomarkers: []

last_reviewed: null
notes: >
  Co-mutations with TP53, STK11, KEAP1 may modulate response. STK11 +
  KRAS G12C predicts poorer ICI response.
"""),
    ("bio_pdl1_tps.yaml", """\
id: BIO-PDL1-TPS
names:
  preferred: "PD-L1 Tumor Proportion Score (TPS)"
  ukrainian: "PD-L1 Tumor Proportion Score (TPS)"
codes:
  loinc: null

biomarker_type: protein_expression_ihc

measurement:
  method: "IHC (22C3, SP263, SP142, 28-8 — pembrolizumab uses 22C3)"
  units: "percent of viable tumor cells with membranous PD-L1 staining"
  typical_range: [0, 100]

interpretation_notes: >
  NSCLC strata:
  • TPS ≥50%: pembrolizumab monotherapy 1L candidate (KEYNOTE-024)
  • TPS 1-49%: pembro + chemo (KEYNOTE-189 / 407) preferred
  • TPS <1%: pembro + chemo OR chemo alone; ICI benefit smaller
  Note: TPS assesses tumor cells only, distinct from CPS (combined
  positive score) used in some other tumors.

related_biomarkers: []

last_reviewed: null
notes: >
  Universal at metastatic NSCLC diagnosis. Distinguishes ICI-monotherapy
  candidates from combination-therapy population.
"""),
]


# ── 5. Tests (3 new) ─────────────────────────────────────────────────


TESTS: list[tuple[str, str]] = [
    ("test_nsclc_ngs_panel.yaml", """\
id: TEST-NSCLC-NGS-PANEL
names:
  preferred: "NSCLC comprehensive NGS panel (DNA + RNA fusion)"
  ukrainian: "NSCLC комплексна NGS панель (ДНК + РНК-фузії)"
test_type: molecular_somatic
priority_class: critical
specimen: "FFPE tumor block (minimum 200 cells; preferred ≥40% tumor content) OR plasma for ctDNA"
turnaround_hours_typical: 336
measures:
  - BIO-EGFR-MUTATION
  - BIO-ALK-FUSION
  - BIO-ROS1-FUSION
  - BIO-KRAS-G12C
  - BIO-BRAF-V600E
sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-METASTATIC-2024]
last_reviewed: null
notes: >
  Universal at advanced NSCLC diagnosis. Panel must cover EGFR (incl
  T790M), ALK, ROS1, KRAS G12C, BRAF V600E, MET ex14, RET, NTRK 1/2/3,
  HER2, NRG1. RNA-based fusion calls preferred for ALK/ROS1/RET/NTRK.
  ctDNA acceptable when tissue inadequate; tissue more sensitive.
  UA-availability concentrated in private labs + academic centers;
  funding pathway barrier.
"""),
    ("test_pdl1_ihc.yaml", """\
id: TEST-PDL1-IHC
names:
  preferred: "PD-L1 IHC (TPS for NSCLC)"
  ukrainian: "PD-L1 ІГХ (TPS для НДРЛ)"
test_type: pathology_ihc
priority_class: critical
specimen: "FFPE tumor tissue"
turnaround_hours_typical: 72
measures: [BIO-PDL1-TPS]
sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-METASTATIC-2024]
last_reviewed: null
notes: >
  22C3 antibody is companion diagnostic for pembrolizumab. SP263 / SP142
  acceptable analytically; institutional preference. Reflex at advanced
  NSCLC diagnosis, parallel to NGS.
"""),
    ("test_brain_mri_contrast.yaml", """\
id: TEST-BRAIN-MRI-CONTRAST
names:
  preferred: "Brain MRI with contrast"
  ukrainian: "МРТ головного мозку з контрастом"
test_type: imaging_mri
priority_class: standard
specimen: "Whole-brain MRI with gadolinium contrast"
turnaround_hours_typical: 48
measures: []
sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-METASTATIC-2024]
last_reviewed: null
notes: >
  Required for NSCLC staging in: stage III considered for curative
  intent, stage IV with neurologic symptoms, ALK / ROS1 / EGFR (high
  CNS-met rates) at baseline + serial monitoring. CT-only acceptable
  if MRI contraindicated. Alias TEST-MRI-BRAIN-CONTRAST exists in some
  references (lymphoma branch) — kept distinct here for solid-tumor
  staging context.
"""),
]


# ── 6. Workup (1 — NSCLC; SCLC reuses) ────────────────────────────────


WORKUP = """\
id: WORKUP-NSCLC-DIAGNOSIS
applicable_to:
  lineage_hints:
    - solid_tumor_lung_nsclc
    - solid_tumor_lung_sclc
    - lung_mass
    - lung_cancer_suspect
  tissue_locations:
    - lung
    - hilar_lymph_nodes
    - mediastinal_lymph_nodes
  presentation_keywords:
    - lung_mass
    - lung_nodule
    - lung_cancer_suspect
    - hemoptysis
    - persistent_cough
    - solitary_pulmonary_nodule

required_tests:
  - TEST-CECT-CAP
  - TEST-PDL1-IHC
  - TEST-NSCLC-NGS-PANEL

desired_tests:
  - TEST-BRAIN-MRI-CONTRAST
  - TEST-PET-CT
  - TEST-BONE-SCAN
  - TEST-GERMLINE-BRCA-PANEL

triggers_mdt_roles:
  required:
    - medical_oncologist
    - thoracic_surgeon
    - radiation_oncologist
    - pathologist
  recommended:
    - radiologist
    - molecular_geneticist
    - nuclear_medicine_specialist
  rationale_per_role:
    medical_oncologist: "Systemic therapy planning across stages."
    thoracic_surgeon: "Resectability + nodal staging assessment for stage I-III."
    radiation_oncologist: "CRT planning for stage III, palliative RT for symptomatic mets."
    pathologist: "Histology + IHC + biomarker reporting."
    radiologist: "Staging interpretation; brain MRI integration."
    molecular_geneticist: "NGS panel + fusion testing oversight."
    nuclear_medicine_specialist: "PET/CT for staging + response assessment."

sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-METASTATIC-2024, SRC-ESMO-NSCLC-EARLY-2024]

last_reviewed: null
notes: >
  Comprehensive NSCLC workup. Universal NGS + PD-L1 at advanced disease
  per NCCN 2025. Brain MRI essential for stage III curative-intent or
  any stage IV. SCLC workup overlaps significantly — reuses this workup
  with stage-specific imaging additions.
"""


# ── 7. Regimens (~10) ────────────────────────────────────────────────


REGIMENS: list[tuple[str, str]] = [
    ("reg_osimertinib_nsclc.yaml", """\
id: REG-OSIMERTINIB-NSCLC
name: "Osimertinib monotherapy (EGFR-mut NSCLC, 1L metastatic OR adjuvant)"
name_ua: "Осимертиніб моно (EGFR-мут НДРЛ, 1L метастатичний АБО ад'ювант)"
alternate_names: ["FLAURA regimen", "ADAURA regimen"]

components:
  - drug_id: DRUG-OSIMERTINIB
    dose: "80 mg PO once daily"
    schedule: "Continuous"
    route: PO

cycle_length_days: 28
total_cycles: "Continuous until progression (metastatic) OR 3 years (ADAURA adjuvant)"
toxicity_profile: low-moderate

premedication: []
mandatory_supportive_care: []
monitoring_schedule_id: null

dose_adjustments:
  - condition: "QTc >500 ms"
    modification: "Hold; resume at 40 mg when normalized"
  - condition: "Pneumonitis any grade"
    modification: "Hold; corticosteroids; permanent discontinuation if severe / recurrent"
  - condition: "LVEF decline"
    modification: "Cardiology consult"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: false
  notes: "Registered; reimbursement under negotiation. Out-of-pocket for most patients in Ukraine — major access barrier for EGFR-mut metastatic + adjuvant indications."

sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-METASTATIC-2024]
last_reviewed: null
notes: >
  FLAURA: superior PFS/OS vs 1G TKIs in 1L EGFR-mut metastatic.
  FLAURA2: osi + chemo extends PFS further. ADAURA: 3-year adjuvant
  in stage IB-IIIA EGFR-mut resected — 80% reduction in recurrence.
"""),
    ("reg_alectinib_nsclc.yaml", """\
id: REG-ALECTINIB-NSCLC
name: "Alectinib monotherapy (ALK+ NSCLC, 1L metastatic OR adjuvant)"
name_ua: "Алектиніб моно (ALK+ НДРЛ, 1L метастатичний АБО ад'ювант)"
alternate_names: ["ALEX regimen", "ALINA regimen"]

components:
  - drug_id: DRUG-ALECTINIB
    dose: "600 mg PO BID with food"
    schedule: "Continuous"
    route: PO

cycle_length_days: 28
total_cycles: "Continuous until progression (metastatic) OR 2 years (ALINA adjuvant)"
toxicity_profile: low-moderate

premedication: []
mandatory_supportive_care: []
monitoring_schedule_id: null

dose_adjustments:
  - condition: "Severe hepatic impairment (Child-Pugh C)"
    modification: "Reduce to 450 mg BID"
  - condition: "Bradycardia"
    modification: "Hold if symptomatic; reduce dose"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: false
  notes: "Registered; reimbursement under negotiation. Out-of-pocket; major access barrier for ALK+ population."

sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-METASTATIC-2024]
last_reviewed: null
notes: >
  ALEX: superior to crizotinib 1L (PFS 35 vs 11 months; intracranial
  response 81 vs 50%). ALINA: 2-year adjuvant in ALK+ stage IB-IIIA
  resected.
"""),
    ("reg_lorlatinib_nsclc.yaml", """\
id: REG-LORLATINIB-NSCLC
name: "Lorlatinib monotherapy (ALK+ NSCLC, 1L OR post-2G TKI)"
name_ua: "Лорлатініб моно (ALK+ НДРЛ, 1L АБО після 2G TKI)"
alternate_names: ["CROWN regimen"]

components:
  - drug_id: DRUG-LORLATINIB
    dose: "100 mg PO once daily"
    schedule: "Continuous"
    route: PO

cycle_length_days: 28
total_cycles: "Continuous until progression"
toxicity_profile: moderate

premedication:
  - "Statin therapy when triglycerides / cholesterol elevated (very common)"
mandatory_supportive_care: []
monitoring_schedule_id: null

dose_adjustments:
  - condition: "G3 cognitive AE"
    modification: "Hold; resume at 75 mg or 50 mg with neuro consult"
  - condition: "Severe hypertriglyceridemia"
    modification: "Statin / fibrate; do not discontinue if managed"

ukraine_availability:
  all_components_registered: false
  all_components_reimbursed: false
  notes: "Not registered in Ukraine. Off-label access; major barrier."

sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-METASTATIC-2024]
last_reviewed: null
notes: >
  CROWN: 3-year PFS 64% (lorlatinib) vs 19% (crizotinib) — most active
  ALK 1L. Cognitive AE management requires careful patient selection.
"""),
    ("reg_pembro_mono_nsclc.yaml", """\
id: REG-PEMBRO-MONO-NSCLC
name: "Pembrolizumab monotherapy (NSCLC PD-L1 ≥50%, driver-negative, 1L)"
name_ua: "Пембролізумаб моно (НДРЛ PD-L1 ≥50%, driver-negative, 1L)"
alternate_names: ["KEYNOTE-024 regimen"]

components:
  - drug_id: DRUG-PEMBROLIZUMAB
    dose: "200 mg IV q3 weeks (or 400 mg q6 weeks)"
    schedule: "Continuous until progression OR 2 years"
    route: IV

cycle_length_days: 21
total_cycles: "Up to 2 years (35 cycles q3w) — KEYNOTE-024 protocol"
toxicity_profile: moderate

premedication: []
mandatory_supportive_care: []
monitoring_schedule_id: null

dose_adjustments:
  - condition: "Immune-mediated AE G≥2"
    modification: "Hold; corticosteroids; discontinue if recurrent G3+"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: false
  notes: "Registered; reimbursement varies by indication. Out-of-pocket for many."

sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-METASTATIC-2024]
last_reviewed: null
notes: >
  KEYNOTE-024: pembro mono superior to platinum-doublet chemo in
  PD-L1≥50% driver-negative metastatic NSCLC (5-year OS ~32% vs 16%).
"""),
    ("reg_pembro_chemo_nsclc_nonsq.yaml", """\
id: REG-PEMBRO-CHEMO-NSCLC-NONSQ
name: "Pembrolizumab + carboplatin + pemetrexed (NSCLC non-squamous, 1L)"
name_ua: "Пембролізумаб + карбоплатин + пеметрексед (НДРЛ non-sq, 1L)"
alternate_names: ["KEYNOTE-189 regimen"]

components:
  - drug_id: DRUG-PEMBROLIZUMAB
    dose: "200 mg IV q3 weeks"
    schedule: "Continuous up to 2 years"
    route: IV
  - drug_id: DRUG-CARBOPLATIN
    dose: "AUC 5 IV"
    schedule: "Cycles 1-4"
    route: IV
  - drug_id: DRUG-PEMETREXED
    dose: "500 mg/m² IV"
    schedule: "Cycles 1-4 + maintenance until progression"
    route: IV

cycle_length_days: 21
total_cycles: "4 cycles induction; then pembro + pemetrexed maintenance until progression OR 2 years total pembro"
toxicity_profile: moderate-severe

premedication:
  - "Folic acid 400-1000 mcg PO daily + Vit B12 1000 mcg IM q9 weeks (pemetrexed)"
  - "Dexamethasone 4 mg PO BID days 0, 1, 2 (rash prophylaxis)"
mandatory_supportive_care: []
monitoring_schedule_id: null

dose_adjustments:
  - condition: "Renal impairment (CrCl <45)"
    modification: "Avoid pemetrexed"
  - condition: "Immune-mediated AE"
    modification: "Hold pembro; corticosteroids"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: false
  notes: "Pembrolizumab reimbursement variable; chemo backbone reimbursed. Out-of-pocket for combination."

sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-METASTATIC-2024]
last_reviewed: null
notes: >
  KEYNOTE-189: superior OS in non-sq NSCLC 1L driver-negative
  regardless of PD-L1 status.

  NOTE: DRUG-PEMETREXED not yet in KB — placeholder reference; if
  pemetrexed YAML missing this regimen will surface ref-error. Will be
  created in cross-disease drug pass.
"""),
    ("reg_durva_consolidation_pacific.yaml", """\
id: REG-DURVA-CONSOLIDATION-PACIFIC
name: "Durvalumab consolidation post-CRT (NSCLC stage III unresectable)"
name_ua: "Дурвалумаб консолідація після ХПТ (НДРЛ III ст нерезектабельний)"
alternate_names: ["PACIFIC regimen"]

components:
  - drug_id: DRUG-DURVALUMAB
    dose: "10 mg/kg IV q2 weeks (or 1500 mg flat dose q4 weeks)"
    schedule: "Up to 12 months consolidation"
    route: IV

cycle_length_days: 14
total_cycles: "Up to 12 months consolidation post-CRT"
toxicity_profile: moderate

premedication: []
mandatory_supportive_care: []
monitoring_schedule_id: null

dose_adjustments:
  - condition: "Pneumonitis G≥2"
    modification: "Hold; corticosteroids; permanent discontinuation if recurrent / severe"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: false
  notes: "Registered; reimbursement variable. Out-of-pocket for most patients."

sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-EARLY-2024]
last_reviewed: null
notes: >
  PACIFIC: 5-year OS 43% (durva) vs 33% (placebo) post-concurrent CRT
  in stage III unresectable NSCLC. Standard of care.
"""),
    ("reg_sotorasib_kras.yaml", """\
id: REG-SOTORASIB-KRAS
name: "Sotorasib monotherapy (KRAS G12C+ NSCLC, 2L+)"
name_ua: "Сотерасіб моно (KRAS G12C+ НДРЛ, 2L+)"
alternate_names: ["CodeBreaK regimen"]

components:
  - drug_id: DRUG-SOTORASIB
    dose: "960 mg PO once daily"
    schedule: "Continuous"
    route: PO

cycle_length_days: 28
total_cycles: "Continuous until progression"
toxicity_profile: moderate

premedication: []
mandatory_supportive_care: []
monitoring_schedule_id: null

dose_adjustments:
  - condition: "Hepatic transaminase elevation"
    modification: "Hold; reduce dose"

ukraine_availability:
  all_components_registered: false
  all_components_reimbursed: false
  notes: "Not registered in Ukraine. Off-label access."

sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-METASTATIC-2024]
last_reviewed: null
notes: >
  CodeBreaK 100/200: 2L+ KRAS G12C+ NSCLC.
"""),
    ("reg_dabrafenib_trametinib_nsclc.yaml", """\
id: REG-DABRAFENIB-TRAMETINIB-NSCLC
name: "Dabrafenib + trametinib (BRAF V600E+ NSCLC)"
name_ua: "Дабрафеніб + траметиніб (BRAF V600E+ НДРЛ)"
alternate_names: ["BRF113928 regimen"]

components:
  - drug_id: DRUG-DABRAFENIB
    dose: "150 mg PO BID"
    schedule: "Continuous"
    route: PO
  - drug_id: DRUG-TRAMETINIB
    dose: "2 mg PO once daily"
    schedule: "Continuous"
    route: PO

cycle_length_days: 28
total_cycles: "Continuous until progression"
toxicity_profile: moderate

premedication:
  - "Antipyretics on hand for pyrexia (very common)"
mandatory_supportive_care: []
monitoring_schedule_id: null

dose_adjustments:
  - condition: "Pyrexia ≥38.5°C"
    modification: "Hold both; restart at lower dose"
  - condition: "LVEF decline"
    modification: "Cardiology consult"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: false
  notes: "Registered; reimbursement variable. Out-of-pocket for many."

sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-METASTATIC-2024]
last_reviewed: null
notes: >
  BRF113928: ORR ~64% in 1L BRAF V600E+ NSCLC. Pyrexia management
  dominant clinical challenge.
"""),

    # ─── SCLC regimens ───────────────────────────────────────────────
    ("reg_ep_atezo_sclc.yaml", """\
id: REG-EP-ATEZO-SCLC
name: "Etoposide-platinum + atezolizumab (extensive SCLC, 1L)"
name_ua: "Етопозид-платина + атезолізумаб (поширена SCLC, 1L)"
alternate_names: ["IMpower133 regimen"]

components:
  - drug_id: DRUG-CARBOPLATIN
    dose: "AUC 5 IV"
    schedule: "Day 1 of 21-day cycle x 4 cycles"
    route: IV
  - drug_id: DRUG-ETOPOSIDE
    dose: "100 mg/m² IV"
    schedule: "Days 1, 2, 3 of 21-day cycle x 4 cycles"
    route: IV
  - drug_id: DRUG-ATEZOLIZUMAB
    dose: "1200 mg IV q3 weeks"
    schedule: "Continuous from cycle 1; maintenance after EP discontinuation"
    route: IV

cycle_length_days: 21
total_cycles: "EP × 4; atezolizumab maintenance until progression"
toxicity_profile: severe

premedication:
  - "Antiemetic per high-emetogenic protocol"
mandatory_supportive_care:
  - SUP-G-CSF-PRIMARY-PROPHYLAXIS-PROSTATE
monitoring_schedule_id: null

dose_adjustments:
  - condition: "Febrile neutropenia"
    modification: "G-CSF; subsequent dose reduction"
  - condition: "Immune-mediated AE"
    modification: "Hold atezolizumab; corticosteroids"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: false
  notes: "Atezolizumab reimbursement varies; chemo backbone reimbursed."

sources: [SRC-NCCN-SCLC-2025, SRC-ESMO-SCLC-2021]
last_reviewed: null
notes: >
  IMpower133: median OS 12.3 (EP+atezo) vs 10.3 months (EP alone) in
  extensive SCLC 1L. Cisplatin substitute possible (less common in
  modern practice).
"""),
    ("reg_ep_durva_sclc.yaml", """\
id: REG-EP-DURVA-SCLC
name: "Etoposide-platinum + durvalumab (extensive SCLC, 1L)"
name_ua: "Етопозид-платина + дурвалумаб (поширена SCLC, 1L)"
alternate_names: ["CASPIAN regimen"]

components:
  - drug_id: DRUG-CARBOPLATIN
    dose: "AUC 5-6 IV"
    schedule: "Day 1 of 21-day cycle x 4 cycles"
    route: IV
  - drug_id: DRUG-ETOPOSIDE
    dose: "80-100 mg/m² IV"
    schedule: "Days 1, 2, 3 of 21-day cycle x 4 cycles"
    route: IV
  - drug_id: DRUG-DURVALUMAB
    dose: "1500 mg IV q3 weeks (induction); 1500 mg q4 weeks (maintenance)"
    schedule: "From cycle 1; maintenance until progression"
    route: IV

cycle_length_days: 21
total_cycles: "EP × 4; durva maintenance until progression"
toxicity_profile: severe

premedication:
  - "Antiemetic per high-emetogenic protocol"
mandatory_supportive_care:
  - SUP-G-CSF-PRIMARY-PROPHYLAXIS-PROSTATE
monitoring_schedule_id: null

dose_adjustments:
  - condition: "Same as EP+atezo"
    modification: "Per drug-specific guidance"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: false
  notes: "Durvalumab reimbursement variable."

sources: [SRC-NCCN-SCLC-2025, SRC-ESMO-SCLC-2021]
last_reviewed: null
notes: >
  CASPIAN: median OS 13.0 (durva) vs 10.3 months (EP). ESMO preferred
  ICI; NCCN considers atezo and durva equivalent.
"""),
    ("reg_ep_concurrent_rt_sclc_limited.yaml", """\
id: REG-EP-CONCURRENT-RT-SCLC-LIMITED
name: "Etoposide-platinum + concurrent thoracic RT (limited SCLC)"
name_ua: "Етопозид-платина + одночасна торакальна променева (обмежена SCLC)"
alternate_names: ["CONVERT regimen"]

components:
  - drug_id: DRUG-CISPLATIN
    dose: "75 mg/m² IV"
    schedule: "Day 1 of 21-day cycle x 4 cycles"
    route: IV
  - drug_id: DRUG-ETOPOSIDE
    dose: "100 mg/m² IV"
    schedule: "Days 1, 2, 3 of 21-day cycle x 4 cycles"
    route: IV

cycle_length_days: 21
total_cycles: "4-6 cycles concurrent with thoracic RT (60 Gy/30 fx once-daily OR 45 Gy/30 fx BID)"
toxicity_profile: severe

premedication:
  - "Antiemetic per high-emetogenic protocol"
  - "Hydration for cisplatin"
mandatory_supportive_care:
  - SUP-G-CSF-PRIMARY-PROPHYLAXIS-PROSTATE
monitoring_schedule_id: null

dose_adjustments:
  - condition: "Esophagitis from RT"
    modification: "Symptomatic management; do not interrupt RT unless severe"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: true
  notes: "All chemo components reimbursed; RT availability institutional."

sources: [SRC-NCCN-SCLC-2025, SRC-ESMO-SCLC-2021]
last_reviewed: null
notes: >
  CONVERT: once-daily 60 Gy non-inferior to BID 45 Gy. Concurrent (not
  sequential) chemo+RT improves outcomes. PCI consideration for CR/PR
  patients post-CRT.
"""),
]


# ── 8. RedFlags (5 NSCLC + 3 SCLC) ──────────────────────────────────


REDFLAGS: list[tuple[str, str]] = [
    ("rf_nsclc_organ_dysfunction.yaml", """\
id: RF-NSCLC-ORGAN-DYSFUNCTION
definition: "Pneumonitis history OR active interstitial lung disease (ILD) — limits ICI (pembrolizumab, atezolizumab, durvalumab, nivolumab) and T-DXd; PACIFIC durvalumab consolidation contraindicated if symptomatic post-CRT pneumonitis."
definition_ua: "Анамнез пневмоніту АБО активна інтерстиціальна хвороба легень — обмежує ICI і T-DXd; PACIFIC дурвалумаб консолідація протипоказана при симптоматичному пост-ХПТ пневмоніті."

trigger:
  type: composite_clinical
  any_of:
    - finding: "ild_active_or_history"
      value: true
    - finding: "post_crt_pneumonitis_grade_2_or_higher"
      value: true

clinical_direction: hold
severity: critical
priority: 50
category: organ-dysfunction

relevant_diseases: [DIS-NSCLC]
shifts_algorithm: []

sources:
  - SRC-NCCN-NSCLC-2025
  - SRC-ESMO-NSCLC-METASTATIC-2024

last_reviewed: null
draft: false

notes: >
  Pneumonitis is the most common ICI / T-DXd-related lethal AE.
  Pre-treatment screen + serial monitoring; immediate hold on any
  new respiratory symptoms during ICI therapy.
"""),
    ("rf_nsclc_infection_screening.yaml", """\
id: RF-NSCLC-INFECTION-SCREENING
definition: "Active TB OR latent TB conversion risk — ICI may trigger TB reactivation; pre-treatment IGRA / TST + chest imaging recommended."
definition_ua: "Активний ТБ АБО ризик конверсії латентного — ICI може викликати реактивацію; перед терапією IGRA / TST + рентген грудної клітки."

trigger:
  type: composite_clinical
  any_of:
    - finding: "tb_latent"
      value: "positive"
    - finding: "tb_active"
      value: true

clinical_direction: hold
severity: major
priority: 100
category: infection-screening

relevant_diseases: [DIS-NSCLC]
shifts_algorithm: []

sources:
  - SRC-NCCN-NSCLC-2025
  - SRC-ESMO-NSCLC-METASTATIC-2024

last_reviewed: null
draft: false

notes: >
  Ukraine is an HBV/HCV/TB high-prevalence region — pre-ICI screen
  more important than in low-prevalence settings. HBV reactivation
  risk handled by RF-UNIVERSAL-HBV-REACTIVATION-RISK.
"""),
    ("rf_nsclc_high_risk_biology.yaml", """\
id: RF-NSCLC-HIGH-RISK-BIOLOGY
definition: "Actionable molecular driver detected (EGFR / ALK / ROS1 / KRAS G12C / BRAF V600E / MET ex14 / RET / NTRK / HER2 mut) — driver-targeted TKI / ADC takes precedence over ICI ± chemo regardless of PD-L1 TPS."
definition_ua: "Виявлено таргет-драйвер (EGFR / ALK / ROS1 / KRAS G12C / BRAF V600E / MET ex14 / RET / NTRK / HER2 mut) — таргет-TKI / ADC має перевагу над ICI ± хіміо незалежно від PD-L1 TPS."

trigger:
  type: biomarker
  any_of:
    - finding: "BIO-EGFR-MUTATION"
      value: "positive"
    - finding: "BIO-ALK-FUSION"
      value: "positive"
    - finding: "BIO-ROS1-FUSION"
      value: "positive"
    - finding: "BIO-KRAS-G12C"
      value: "positive"
    - finding: "BIO-BRAF-V600E"
      value: "positive"
    - finding: "met_ex14_skipping"
      value: true
    - finding: "ret_fusion"
      value: true
    - finding: "ntrk_fusion"
      value: true
    - finding: "her2_mutation_nsclc"
      value: true

clinical_direction: intensify
severity: critical
priority: 50
category: high-risk-biology

relevant_diseases: [DIS-NSCLC]
shifts_algorithm: [ALGO-NSCLC-METASTATIC-1L]

sources:
  - SRC-NCCN-NSCLC-2025
  - SRC-ESMO-NSCLC-METASTATIC-2024

last_reviewed: null
draft: false

notes: >
  Driver-mutant NSCLC patients DO NOT benefit from ICI 1L (poorer
  responses, hyperprogression risk) — TKIs/ADCs are markedly superior.
  Universal NGS at diagnosis prevents missed-driver scenarios.
"""),
    ("rf_nsclc_transformation_progression.yaml", """\
id: RF-NSCLC-TRANSFORMATION-PROGRESSION
definition: "Symptomatic CNS metastases OR superior vena cava (SVC) syndrome OR rapid radiographic progression on therapy — emergency / aggressive-progression flag requiring brain imaging, RT/surgical consult, and treatment intensification or sequencing change."
definition_ua: "Симптоматичні метастази в ЦНС АБО синдром верхньої порожнистої вени (SVC) АБО швидке радіографічне прогресування на терапії — невідкладний / агресивно-прогресуючий тригер."

trigger:
  type: composite_clinical
  any_of:
    - finding: "symptomatic_cns_metastases"
      value: true
    - finding: "svc_syndrome"
      value: true
    - finding: "rapid_radiographic_progression_nsclc"
      value: true

clinical_direction: hold
severity: critical
priority: 50
category: transformation-progression

relevant_diseases: [DIS-NSCLC]
shifts_algorithm: []

sources:
  - SRC-NCCN-NSCLC-2025
  - SRC-ESMO-NSCLC-METASTATIC-2024

last_reviewed: null
draft: false

notes: >
  CNS-active TKI options critical for ALK / EGFR / ROS1 mets — alectinib /
  lorlatinib / brigatinib / osimertinib all have CNS efficacy. SVC syndrome:
  emergent RT or stenting; systemic therapy proceeds in parallel.
"""),
    ("rf_nsclc_frailty_age.yaml", """\
id: RF-NSCLC-FRAILTY-AGE
definition: "Age ≥75 + ECOG ≥2 + significant comorbidity — concurrent CRT and platinum-doublet chemo poorly tolerated; consider sequential CRT, weekly chemo + ICI, or single-agent / best-supportive-care for fragile patients."
definition_ua: "Вік ≥75 + ECOG ≥2 + суттєві коморбідності — одночасна ХПТ і платиновий дублет погано переносяться; розглянути послідовну ХПТ, тижневу хіміо + ICI, або моно / best-supportive-care."

trigger:
  type: composite_clinical
  all_of:
    - finding: "age_years"
      threshold: 75
      comparator: ">="
    - any_of:
        - finding: "ecog_status"
          threshold: 2
          comparator: ">="
        - finding: "comorbidity_count"
          threshold: 2
          comparator: ">="

clinical_direction: de-escalate
severity: major
priority: 100
category: frailty-age

relevant_diseases: [DIS-NSCLC]
shifts_algorithm: []

sources:
  - SRC-NCCN-NSCLC-2025
  - SRC-ESMO-NSCLC-EARLY-2024

last_reviewed: null
draft: false

notes: >
  Geriatric assessment (G8 / CGA) recommended pre-treatment for ≥70.
  PD-L1≥50% driver-negative elderly: pembrolizumab mono is the
  best-tolerated option preserving OS benefit.
"""),

    # SCLC RFs — fewer (3) given simpler treatment paradigm
    ("rf_sclc_organ_dysfunction.yaml", """\
id: RF-SCLC-ORGAN-DYSFUNCTION
definition: "Renal dysfunction (CrCl <50) OR severe hepatic impairment — limits cisplatin (use carboplatin AUC 5); dose-modify etoposide for liver impairment."
definition_ua: "Ниркова дисфункція (CrCl <50) АБО тяжке печінкове порушення — обмежує цисплатин (use карбоплатин AUC 5); модифікація етопозиду при печінковому порушенні."

trigger:
  type: composite_clinical
  any_of:
    - finding: "creatinine_clearance_ml_min"
      threshold: 50
      comparator: "<"
    - finding: "child_pugh_class"
      value: "C"

clinical_direction: investigate
severity: major
priority: 100
category: organ-dysfunction

relevant_diseases: [DIS-SCLC]
shifts_algorithm: []

sources:
  - SRC-NCCN-SCLC-2025
  - SRC-ESMO-SCLC-2021

last_reviewed: null
draft: false

notes: >
  Carboplatin substitution standard for CrCl <50. Liver dysfunction:
  reduce etoposide 50% if bilirubin 1.5-3x ULN; avoid if >3x ULN.
"""),
    ("rf_sclc_paraneoplastic.yaml", """\
id: RF-SCLC-PARANEOPLASTIC
definition: "Paraneoplastic syndrome (SIADH, Cushing's, Lambert-Eaton, autoimmune limbic encephalitis) — common in SCLC; neurology / endocrinology consult; symptomatic management may delay or modify systemic therapy initiation."
definition_ua: "Паранеопластичний синдром (SIADH, Кушинг, Lambert-Eaton, автоімунний лімбічний енцефаліт) — поширений у SCLC; неврологія / ендокринологія; симптоматичне лікування може відстрочити / модифікувати системну терапію."

trigger:
  type: composite_clinical
  any_of:
    - finding: "siadh"
      value: true
    - finding: "cushing_paraneoplastic"
      value: true
    - finding: "lambert_eaton"
      value: true
    - finding: "limbic_encephalitis"
      value: true

clinical_direction: investigate
severity: major
priority: 100
category: transformation-progression

relevant_diseases: [DIS-SCLC]
shifts_algorithm: []

sources:
  - SRC-NCCN-SCLC-2025
  - SRC-ESMO-SCLC-2021

last_reviewed: null
draft: false

notes: >
  Paraneoplastic syndromes affect ~15-25% of SCLC patients. Tumor
  control often resolves the syndrome; severe presentations may
  require pre-systemic-therapy stabilization.
"""),
    ("rf_sclc_frailty_age.yaml", """\
id: RF-SCLC-FRAILTY-AGE
definition: "Age ≥75 + ECOG ≥2 OR significant comorbidity — concurrent CRT (limited-stage) poorly tolerated; sequential CRT or single-agent palliative chemo considered."
definition_ua: "Вік ≥75 + ECOG ≥2 АБО суттєві коморбідності — одночасна ХПТ (обмежена стадія) погано переноситься; послідовна ХПТ або моно паліативна хіміо."

trigger:
  type: composite_clinical
  all_of:
    - finding: "age_years"
      threshold: 75
      comparator: ">="
    - any_of:
        - finding: "ecog_status"
          threshold: 2
          comparator: ">="
        - finding: "comorbidity_count"
          threshold: 2
          comparator: ">="

clinical_direction: de-escalate
severity: major
priority: 100
category: frailty-age

relevant_diseases: [DIS-SCLC]
shifts_algorithm: []

sources:
  - SRC-NCCN-SCLC-2025
  - SRC-ESMO-SCLC-2021

last_reviewed: null
draft: false

notes: >
  Limited-stage SCLC + frailty: sequential CRT (chemo first, then RT)
  better tolerated than concurrent. Extensive-stage + frailty: EP +
  ICI feasible with G-CSF support.
"""),
]


# ── 9. Indications (NSCLC: 6 driver-specific + 2 non-driver; SCLC: 2) ─


INDICATIONS: list[tuple[str, str]] = [
    ("ind_nsclc_egfr_mut_met_1l.yaml", """\
id: IND-NSCLC-EGFR-MUT-MET-1L
plan_track: standard

applicable_to:
  disease_id: DIS-NSCLC
  molecular_subtype: EGFR_MUT
  stage_stratum: STAGE_IV_METASTATIC
  line_of_therapy: 1
  biomarker_requirements_required:
    - biomarker_id: BIO-EGFR-MUTATION
      value_constraint: "positive"
      required: true
  biomarker_requirements_excluded: []
  demographic_constraints:
    ecog_max: 2

recommended_regimen: REG-OSIMERTINIB-NSCLC
concurrent_therapy: []
followed_by: []

evidence_level: high
strength_of_recommendation: strong
nccn_category: "1"

expected_outcomes:
  median_progression_free_survival_months: 19
  median_overall_survival_months: 39
  notes: "FLAURA"

hard_contraindications: []
red_flags_triggering_alternative: []
required_tests: [TEST-NSCLC-NGS-PANEL, TEST-PDL1-IHC, TEST-CECT-CAP]
desired_tests: [TEST-BRAIN-MRI-CONTRAST]

sources:
  - source_id: SRC-NCCN-NSCLC-2025
    weight: primary
  - source_id: SRC-ESMO-NSCLC-METASTATIC-2024
    weight: primary

last_reviewed: null
reviewers: []

notes: >
  Workhorse 1L for EGFR-mut metastatic NSCLC. Osimertinib + chemo
  (FLAURA2) further extends PFS — alternative for high-burden disease.
"""),
    ("ind_nsclc_alk_met_1l.yaml", """\
id: IND-NSCLC-ALK-MET-1L
plan_track: standard

applicable_to:
  disease_id: DIS-NSCLC
  molecular_subtype: ALK_REARRANGED
  stage_stratum: STAGE_IV_METASTATIC
  line_of_therapy: 1
  biomarker_requirements_required:
    - biomarker_id: BIO-ALK-FUSION
      value_constraint: "positive"
      required: true
  biomarker_requirements_excluded: []
  demographic_constraints:
    ecog_max: 2

recommended_regimen: REG-ALECTINIB-NSCLC
concurrent_therapy: []
followed_by: []

evidence_level: high
strength_of_recommendation: strong
nccn_category: "1"

expected_outcomes:
  median_progression_free_survival_months: 35
  median_overall_survival_months: ">5 years (ALEX)"

hard_contraindications: []
red_flags_triggering_alternative: []
required_tests: [TEST-NSCLC-NGS-PANEL, TEST-PDL1-IHC, TEST-CECT-CAP, TEST-BRAIN-MRI-CONTRAST]
desired_tests: []

sources:
  - source_id: SRC-NCCN-NSCLC-2025
    weight: primary
  - source_id: SRC-ESMO-NSCLC-METASTATIC-2024
    weight: primary

last_reviewed: null
reviewers: []

notes: >
  ALEX: alectinib superior to crizotinib. Lorlatinib (CROWN) more
  active but toxicity / cognitive AE profile — alectinib remains
  workhorse 1L; lorlatinib for selected patients.
"""),
    ("ind_nsclc_kras_g12c_met_2l.yaml", """\
id: IND-NSCLC-KRAS-G12C-MET-2L
plan_track: standard

applicable_to:
  disease_id: DIS-NSCLC
  molecular_subtype: KRAS_G12C
  stage_stratum: STAGE_IV_METASTATIC
  line_of_therapy: 2
  biomarker_requirements_required:
    - biomarker_id: BIO-KRAS-G12C
      value_constraint: "positive"
      required: true
  biomarker_requirements_excluded: []
  demographic_constraints:
    ecog_max: 2

recommended_regimen: REG-SOTORASIB-KRAS
concurrent_therapy: []
followed_by: []

evidence_level: high
strength_of_recommendation: strong
nccn_category: "2A"

expected_outcomes:
  median_progression_free_survival_months: 6.5
  notes: "CodeBreaK 200"

hard_contraindications: []
red_flags_triggering_alternative: []
required_tests: [TEST-NSCLC-NGS-PANEL, TEST-CECT-CAP]
desired_tests: [TEST-BRAIN-MRI-CONTRAST]

sources:
  - source_id: SRC-NCCN-NSCLC-2025
    weight: primary
  - source_id: SRC-ESMO-NSCLC-METASTATIC-2024
    weight: primary

last_reviewed: null
reviewers: []

notes: >
  KRAS G12C 2L+ standard. 1L role pending (CodeBreaK 1L trials).
  Adagrasib alternative; preferred for brain mets (better CNS profile).
"""),
    ("ind_nsclc_pdl1_high_met_1l.yaml", """\
id: IND-NSCLC-PDL1-HIGH-MET-1L
plan_track: standard

applicable_to:
  disease_id: DIS-NSCLC
  molecular_subtype: DRIVER_NEGATIVE
  stage_stratum: STAGE_IV_METASTATIC
  pdl1_tps_stratum: TPS_HIGH
  line_of_therapy: 1
  biomarker_requirements_required:
    - biomarker_id: BIO-PDL1-TPS
      value_constraint: "≥50"
      required: true
  biomarker_requirements_excluded: []
  demographic_constraints:
    ecog_max: 2

recommended_regimen: REG-PEMBRO-MONO-NSCLC
concurrent_therapy: []
followed_by: []

evidence_level: high
strength_of_recommendation: strong
nccn_category: "1"

expected_outcomes:
  five_year_overall_survival: "32% pembro mono vs 16% chemo"
  notes: "KEYNOTE-024"

hard_contraindications: []
red_flags_triggering_alternative: []
required_tests: [TEST-NSCLC-NGS-PANEL, TEST-PDL1-IHC, TEST-CECT-CAP]
desired_tests: [TEST-BRAIN-MRI-CONTRAST]

sources:
  - source_id: SRC-NCCN-NSCLC-2025
    weight: primary
  - source_id: SRC-ESMO-NSCLC-METASTATIC-2024
    weight: primary

last_reviewed: null
reviewers: []

notes: >
  Driver-negative + PD-L1≥50%: pembro mono workhorse. Combined
  pembro+chemo also acceptable when high tumor burden / rapid
  progression / visceral crisis.
"""),
    ("ind_nsclc_pdl1_low_nonsq_met_1l.yaml", """\
id: IND-NSCLC-PDL1-LOW-NONSQ-MET-1L
plan_track: aggressive

applicable_to:
  disease_id: DIS-NSCLC
  molecular_subtype: DRIVER_NEGATIVE
  stage_stratum: STAGE_IV_METASTATIC
  pdl1_tps_stratum: TPS_INTERMEDIATE
  line_of_therapy: 1
  biomarker_requirements_required:
    - biomarker_id: BIO-PDL1-TPS
      value_constraint: "<50"
      required: true
  biomarker_requirements_excluded: []
  demographic_constraints:
    ecog_max: 2

recommended_regimen: REG-PEMBRO-CHEMO-NSCLC-NONSQ
concurrent_therapy: []
followed_by: []

evidence_level: high
strength_of_recommendation: strong
nccn_category: "1"

expected_outcomes:
  median_overall_survival_months: 22
  notes: "KEYNOTE-189 (non-squamous)"

hard_contraindications: []
red_flags_triggering_alternative: []
required_tests: [TEST-NSCLC-NGS-PANEL, TEST-PDL1-IHC, TEST-CECT-CAP]
desired_tests: [TEST-BRAIN-MRI-CONTRAST]

sources:
  - source_id: SRC-NCCN-NSCLC-2025
    weight: primary
  - source_id: SRC-ESMO-NSCLC-METASTATIC-2024
    weight: primary

last_reviewed: null
reviewers: []

notes: >
  KEYNOTE-189: pembro + carbo + pemetrexed superior to chemo alone in
  non-squamous PD-L1<50% driver-negative metastatic. KEYNOTE-407
  parallel for squamous (with paclitaxel instead of pemetrexed).
"""),
    ("ind_nsclc_stage_iii_pacific.yaml", """\
id: IND-NSCLC-STAGE-III-PACIFIC
plan_track: standard

applicable_to:
  disease_id: DIS-NSCLC
  stage_stratum: STAGE_III_UNRESECTABLE
  line_of_therapy: 1
  biomarker_requirements_required: []
  biomarker_requirements_excluded: []
  demographic_constraints:
    ecog_max: 1

recommended_regimen: REG-DURVA-CONSOLIDATION-PACIFIC
concurrent_therapy: []
followed_by: []

evidence_level: high
strength_of_recommendation: strong
nccn_category: "1"

expected_outcomes:
  five_year_overall_survival: "43% durva vs 33% placebo"
  notes: "PACIFIC"

hard_contraindications: []
red_flags_triggering_alternative:
  - RF-NSCLC-ORGAN-DYSFUNCTION
required_tests: [TEST-NSCLC-NGS-PANEL, TEST-PDL1-IHC, TEST-CECT-CAP, TEST-BRAIN-MRI-CONTRAST]
desired_tests: []

sources:
  - source_id: SRC-NCCN-NSCLC-2025
    weight: primary
  - source_id: SRC-ESMO-NSCLC-EARLY-2024
    weight: primary

last_reviewed: null
reviewers: []

notes: >
  Standard for stage III unresectable post-concurrent CRT. Pneumonitis
  G≥2 at end of CRT excludes durva initiation.
"""),
    ("ind_sclc_extensive_1l.yaml", """\
id: IND-SCLC-EXTENSIVE-1L
plan_track: standard

applicable_to:
  disease_id: DIS-SCLC
  stage_stratum: EXTENSIVE
  line_of_therapy: 1
  biomarker_requirements_required: []
  biomarker_requirements_excluded: []
  demographic_constraints:
    ecog_max: 2

recommended_regimen: REG-EP-DURVA-SCLC
concurrent_therapy: []
followed_by: []

evidence_level: high
strength_of_recommendation: strong
nccn_category: "1"

expected_outcomes:
  median_overall_survival_months: 13
  notes: "CASPIAN"

hard_contraindications: []
red_flags_triggering_alternative:
  - RF-SCLC-FRAILTY-AGE
required_tests: [TEST-CECT-CAP, TEST-BRAIN-MRI-CONTRAST]
desired_tests: []

sources:
  - source_id: SRC-NCCN-SCLC-2025
    weight: primary
  - source_id: SRC-ESMO-SCLC-2021
    weight: primary

last_reviewed: null
reviewers: []

notes: >
  CASPIAN durvalumab preferred per ESMO; NCCN considers EP+atezo
  (IMpower133) and EP+durva (CASPIAN) equivalent. Choice institutional.
"""),
    ("ind_sclc_limited_1l.yaml", """\
id: IND-SCLC-LIMITED-1L
plan_track: standard

applicable_to:
  disease_id: DIS-SCLC
  stage_stratum: LIMITED
  line_of_therapy: 1
  biomarker_requirements_required: []
  biomarker_requirements_excluded: []
  demographic_constraints:
    ecog_max: 1

recommended_regimen: REG-EP-CONCURRENT-RT-SCLC-LIMITED
concurrent_therapy: []
followed_by: []

evidence_level: high
strength_of_recommendation: strong
nccn_category: "1"

expected_outcomes:
  median_overall_survival_months: 27
  notes: "CONVERT once-daily 60 Gy"

hard_contraindications: []
red_flags_triggering_alternative:
  - RF-SCLC-FRAILTY-AGE
required_tests: [TEST-CECT-CAP, TEST-BRAIN-MRI-CONTRAST]
desired_tests: []

sources:
  - source_id: SRC-NCCN-SCLC-2025
    weight: primary
  - source_id: SRC-ESMO-SCLC-2021
    weight: primary

last_reviewed: null
reviewers: []

notes: >
  Concurrent CRT — superior to sequential. PCI consideration for CR/PR
  post-CRT.
"""),
]


# ── 10. Algorithms (2) ──────────────────────────────────────────────


ALGORITHMS: list[tuple[str, str]] = [
    ("algo_nsclc_metastatic_1l.yaml", """\
id: ALGO-NSCLC-METASTATIC-1L
applicable_to_disease: DIS-NSCLC
applicable_to_line_of_therapy: 1
purpose: >
  Select 1L metastatic NSCLC regimen via molecular-cascade decision
  tree: actionable driver → driver-targeted TKI/ADC; driver-negative →
  PD-L1 TPS → ICI strategy. Stage III unresectable handled in separate
  Algorithm.

output_indications:
  - IND-NSCLC-EGFR-MUT-MET-1L
  - IND-NSCLC-ALK-MET-1L
  - IND-NSCLC-KRAS-G12C-MET-2L
  - IND-NSCLC-PDL1-HIGH-MET-1L
  - IND-NSCLC-PDL1-LOW-NONSQ-MET-1L

default_indication: IND-NSCLC-PDL1-LOW-NONSQ-MET-1L
alternative_indication: IND-NSCLC-PDL1-HIGH-MET-1L

decision_tree:
  - step: 1
    evaluate:
      any_of:
        - red_flag: RF-NSCLC-HIGH-RISK-BIOLOGY
    if_true:
      next_step: 2
    if_false:
      next_step: 5
  - step: 2
    evaluate:
      any_of:
        - condition: "EGFR mutation positive"
    if_true:
      result: IND-NSCLC-EGFR-MUT-MET-1L
    if_false:
      next_step: 3
  - step: 3
    evaluate:
      any_of:
        - condition: "ALK rearrangement positive"
    if_true:
      result: IND-NSCLC-ALK-MET-1L
    if_false:
      next_step: 4
  - step: 4
    evaluate:
      any_of:
        - condition: "Other actionable driver (ROS1 / KRAS G12C / BRAF / MET / RET / NTRK / HER2-mut)"
    if_true:
      result: IND-NSCLC-KRAS-G12C-MET-2L
    if_false:
      next_step: 5
  - step: 5
    evaluate:
      any_of:
        - condition: "PD-L1 TPS ≥50%"
    if_true:
      result: IND-NSCLC-PDL1-HIGH-MET-1L
    if_false:
      result: IND-NSCLC-PDL1-LOW-NONSQ-MET-1L

sources: [SRC-NCCN-NSCLC-2025, SRC-ESMO-NSCLC-METASTATIC-2024]
last_reviewed: null
notes: >
  Decision tree intentionally simplified for MVP. KRAS G12C step routes
  to KRAS-G12C-MET-2L (which is 2L+ per current guidelines); for true
  1L driver-targeting of ROS1 / BRAF / MET / RET / NTRK / HER2, additional
  per-driver indications would be required (deferred). Driver-negative
  branches into PD-L1-stratified ICI ± chemo.
"""),
    ("algo_sclc_1l.yaml", """\
id: ALGO-SCLC-1L
applicable_to_disease: DIS-SCLC
applicable_to_line_of_therapy: 1
purpose: >
  Select 1L SCLC regimen by stage: limited → EP + concurrent RT;
  extensive → EP + ICI (durvalumab or atezolizumab).

output_indications:
  - IND-SCLC-EXTENSIVE-1L
  - IND-SCLC-LIMITED-1L

default_indication: IND-SCLC-EXTENSIVE-1L
alternative_indication: IND-SCLC-LIMITED-1L

decision_tree:
  - step: 1
    evaluate:
      any_of:
        - condition: "Limited-stage (one hemithorax + tolerable RT field)"
    if_true:
      result: IND-SCLC-LIMITED-1L
    if_false:
      result: IND-SCLC-EXTENSIVE-1L

sources: [SRC-NCCN-SCLC-2025, SRC-ESMO-SCLC-2021]
last_reviewed: null
notes: >
  Stage-driven binary fork. Frailty (RF-SCLC-FRAILTY-AGE) triggers
  sequential rather than concurrent CRT for limited; reduced-intensity
  EP+ICI for extensive.
"""),
]


# ── DRIVER ─────────────────────────────────────────────────────────────


def main() -> int:
    write("diseases/nsclc.yaml", DISEASE_NSCLC)
    write("diseases/sclc.yaml", DISEASE_SCLC)
    for fname, body in SOURCES.items():
        write(f"sources/{fname}", body)
    for fname, body in DRUGS:
        write(f"drugs/{fname}", body)
    for fname, body in BIOMARKERS:
        write(f"biomarkers/{fname}", body)
    for fname, body in TESTS:
        write(f"tests/{fname}", body)
    write("workups/workup_nsclc_diagnosis.yaml", WORKUP)
    for fname, body in REGIMENS:
        write(f"regimens/{fname}", body)
    for fname, body in REDFLAGS:
        write(f"redflags/{fname}", body)
    for fname, body in INDICATIONS:
        write(f"indications/{fname}", body)
    for fname, body in ALGORITHMS:
        write(f"algorithms/{fname}", body)
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
