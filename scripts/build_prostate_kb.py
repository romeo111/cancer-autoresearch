"""Generate the full Prostate-cancer KB vertical.

Emits Disease + Drugs + Biomarkers + Tests + Workup + Regimens +
Indications + Algorithm + RedFlags + Contraindications + SupportiveCare +
Sources required for prostate cancer end-to-end.

Per CHARTER §8.3 this is *extraction* from cited NCCN/ESMO/AUA/EAU
guidelines, not LLM clinical decision-making. Two-reviewer merge gate
per §6.1 still applies; everything authored as `last_reviewed: null`,
`reviewers: []`.

Run:
    python scripts/build_prostate_kb.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
KB = REPO_ROOT / "knowledge_base" / "hosted" / "content"


# ── helper ─────────────────────────────────────────────────────────────


def write(rel: str, body: str) -> None:
    target = KB / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    print(f"wrote {rel}")


# ── 1. Disease ─────────────────────────────────────────────────────────


DISEASE = """\
id: DIS-PROSTATE
names:
  preferred: "Prostate adenocarcinoma"
  ukrainian: "Аденокарцинома передміхурової залози"
  english: "Prostate adenocarcinoma"
  synonyms: ["Prostate cancer", "PCa", "РПЗ"]

codes:
  icd_o_3_morphology: "8140/3"
  icd_o_3_topography: ["C61.9"]
  icd_10: "C61"
  who_classification: "Acinar adenocarcinoma of the prostate (WHO 5th)"

archetype: line_of_therapy_sequential
lineage: solid_tumor_prostate

# Sub-strata are line-of-therapy / disease-state combinations rather than
# molecular subtypes. The Algorithm decision_tree resolves which stratum
# applies for a given patient.
disease_states:
  - id: nmCRPC
    label: "Non-metastatic castration-resistant prostate cancer"
    label_ua: "Неметастатичний кастраційно-резистентний РПЗ"
    definition: "Rising PSA on ADT with castrate testosterone (<50 ng/dL), no radiographic metastases"
  - id: mHSPC
    label: "Metastatic hormone-sensitive prostate cancer"
    label_ua: "Метастатичний гормоночутливий РПЗ"
    definition: "De-novo or recurrent metastatic disease before castration resistance develops"
  - id: mCRPC
    label: "Metastatic castration-resistant prostate cancer"
    label_ua: "Метастатичний кастраційно-резистентний РПЗ"
    definition: "Progression on ADT with castrate testosterone; PSA progression and/or radiographic progression"

# Risk-stratification frameworks used downstream
prognostic_frameworks:
  - id: NCCN-PROSTATE-RISK
    label: "NCCN risk groups (very-low / low / intermediate-favorable / intermediate-unfavorable / high / very-high)"
    used_for: "localized disease — drives RT vs surveillance vs RP decisions; out of scope for this MVP which focuses on advanced disease"
  - id: CHAARTED-VOLUME
    label: "CHAARTED volume criteria (high-volume = visceral metastases OR ≥4 bone lesions with ≥1 beyond axial skeleton)"
    used_for: "mHSPC docetaxel-add decision"
  - id: LATITUDE-RISK
    label: "LATITUDE high-risk (≥2 of: Gleason ≥8, ≥3 bone lesions, visceral metastases)"
    used_for: "mHSPC abiraterone-add decision"

etiological_factors:
  - "Androgen-driven proliferation — testosterone / DHT via androgen receptor"
  - "Germline DNA-repair defects (BRCA1/2, ATM, CHEK2, PALB2) ~5-15% of metastatic — predict PARPi response and aggressive course"
  - "Somatic HRR alterations (BRCA, ATM, CDK12, FANC family) up to 25% in mCRPC"
  - "TMPRSS2-ERG fusions ~50% but no current therapeutic actionability"

related_diseases: []

epidemiology:
  context: >
    Most common solid tumor in men globally (~1.4M/year). Median age at
    diagnosis ~67. Vast majority (~95%) acinar adenocarcinoma. Localized
    disease has excellent 10-y OS (>95%); metastatic 5-y OS ~30-40%, but
    modern combinations (ADT + ARPI ± docetaxel ± PARPi for HRR-mutant)
    have substantially improved mCRPC OS. Indolent natural history of
    low-risk localized disease enables active surveillance — large UA
    practice gap is access to germline BRCA testing for PARPi eligibility.

sources:
  - SRC-NCCN-PROSTATE-2025
  - SRC-ESMO-PROSTATE-2024
  - SRC-EAU-PROSTATE-2024

last_reviewed: null
reviewers: []
notes: >
  Coverage scope MVP: advanced disease (mHSPC + mCRPC + nmCRPC).
  Localized disease (active surveillance, RP, definitive RT, brachytherapy)
  intentionally out of scope — would require urology workflow modeling
  beyond current architecture.
"""

# ── 2. Sources (3 new) ─────────────────────────────────────────────────


SOURCES: dict[str, str] = {
    "src_nccn_prostate_2025.yaml": """\
id: SRC-NCCN-PROSTATE-2025
source_type: guideline
title: NCCN Clinical Practice Guidelines — Prostate Cancer
version: '2025.v3'
authors:
  - National Comprehensive Cancer Network
journal: null
doi: null
url: https://www.nccn.org/professionals/physician_gls/pdf/prostate.pdf
access_level: registration_required
currency_status: current
superseded_by: null
current_as_of: '2025-09-01'
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
  name: NCCN — clinician-only redistribution prohibited
  url: https://www.nccn.org/permissions
  spdx_id: null
attribution:
  required: true
  text: 'NCCN Clinical Practice Guidelines: Prostate Cancer v.3.2025'
commercial_use_allowed: false
redistribution_allowed: false
modifications_allowed: false
sharealike_required: false
known_restrictions:
  - 'NCCN: derivative work prohibited; quote-paraphrase model only'
legal_review:
  status: pending
  reviewer: null
  date: null
  notes: Same posture as SRC-NCCN-BCELL-2025
relates_to_diseases:
  - DIS-PROSTATE
last_verified: null
notes: >
  Primary international guideline for prostate cancer. Codifies NCCN
  risk-group stratification (very-low → very-high), ADT + ARPI + docetaxel
  combinations for mHSPC, abiraterone/enzalutamide for mCRPC 1L,
  PARPi (olaparib, rucaparib, talazoparib) for HRR-mutant mCRPC,
  Lu-177-PSMA for PSMA-positive mCRPC post-ARPI/post-taxane,
  radium-223 for symptomatic bone-predominant mCRPC, darolutamide /
  enzalutamide / apalutamide for nmCRPC.
pages_count: 250
references_count: 600
corpus_role: primary_guideline
""",
    "src_esmo_prostate_2024.yaml": """\
id: SRC-ESMO-PROSTATE-2024
source_type: guideline
title: ESMO Clinical Practice Guideline on Prostate Cancer
version: '2024'
authors:
  - ESMO Guidelines Committee
journal: Annals of Oncology
doi: null
url: https://www.esmo.org/guidelines/guidelines-by-topic/genitourinary-cancers/prostate-cancer
access_level: open_access
currency_status: current
superseded_by: null
current_as_of: '2024-10-01'
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
  name: CC-BY-NC-ND 4.0 (typical for ESMO / Annals of Oncology)
  url: https://creativecommons.org/licenses/by-nc-nd/4.0/
  spdx_id: CC-BY-NC-ND-4.0
attribution:
  required: true
  text: 'ESMO Clinical Practice Guideline: Prostate Cancer, 2024'
commercial_use_allowed: false
redistribution_allowed: false
modifications_allowed: false
sharealike_required: false
known_restrictions:
  - 'CC-BY-NC-ND: derivative-work interpretation pending legal review'
legal_review:
  status: pending
  reviewer: null
  date: null
  notes: Same posture as SRC-ESMO-DLBCL-2024
relates_to_diseases:
  - DIS-PROSTATE
last_verified: null
notes: >
  Primary international guideline for prostate cancer. Detailed mHSPC
  stratification (CHAARTED + LATITUDE), mCRPC sequencing, biomarker-driven
  PARPi indications, PSMA-radioligand therapy positioning.
pages_count: 28
references_count: 195
corpus_role: primary_guideline
""",
    "src_eau_prostate_2024.yaml": """\
id: SRC-EAU-PROSTATE-2024
source_type: guideline
title: EAU - EANM - ESTRO - ESUR - ISUP - SIOG Guidelines on Prostate Cancer
version: '2024'
authors:
  - European Association of Urology Guidelines Office
journal: null
doi: null
url: https://uroweb.org/guidelines/prostate-cancer
access_level: open_access
currency_status: current
superseded_by: null
current_as_of: '2024-04-01'
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
  name: EAU usage license — non-commercial reproduction with attribution
  url: https://uroweb.org/guidelines
  spdx_id: null
attribution:
  required: true
  text: 'EAU Guidelines on Prostate Cancer, 2024'
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
  notes: Posture analogous to NCCN
relates_to_diseases:
  - DIS-PROSTATE
last_verified: null
notes: >
  Pan-European multi-society guideline integrating urology, nuclear
  medicine, RT, radiology, pathology, and geriatric perspectives. Strong
  on PSMA-PET imaging integration and surgical staging which NCCN/ESMO
  cover less deeply.
pages_count: 230
references_count: 500
corpus_role: primary_guideline
""",
}

# ── 3. Drugs (15) ─────────────────────────────────────────────────────


DRUG_TEMPLATE = """\
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

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  {notes}
"""


def _drug(
    id_: str,
    preferred: str,
    ukrainian: str,
    brands: list[str],
    atc: str,
    drug_class: str,
    mechanism: str,
    fda: bool,
    ema: bool,
    ua_registered: bool,
    ua_reimbursed: bool,
    ua_notes: str,
    dosing: str,
    toxicities: list[str],
    notes: str,
) -> str:
    brand_list = "[" + ", ".join(f'"{b}"' for b in brands) + "]" if brands else "[]"
    tox_block = "\n".join(f"  - {t}" for t in toxicities) or "  - (none specific)"
    return DRUG_TEMPLATE.format(
        id=id_,
        preferred=preferred,
        ukrainian=ukrainian,
        brands=brand_list,
        atc=atc,
        drug_class=drug_class,
        mechanism=mechanism,
        fda=str(fda).lower(),
        ema=str(ema).lower(),
        ua_registered=str(ua_registered).lower(),
        ua_reimbursed=str(ua_reimbursed).lower(),
        ua_notes=ua_notes.replace('"', '\\"'),
        dosing=dosing,
        toxicities=tox_block,
        notes=notes,
    )


DRUGS: list[tuple[str, str]] = [
    ("leuprolide.yaml", _drug(
        "DRUG-LEUPROLIDE", "Leuprolide", "Лейпрорелін",
        ["Lupron", "Eligard"], "L02AE02",
        "GnRH agonist (LHRH agonist)",
        "GnRH receptor agonist — initial pituitary stimulation followed by receptor desensitization within 2-4 weeks, suppressing LH/FSH and reducing testicular testosterone production to castrate levels (<50 ng/dL).",
        True, True, True, True,
        "Standard ADT backbone — НСЗУ reimbursed as part of cancer-pathway essential medicines.",
        "3.75 mg IM monthly OR 11.25 mg IM q3 months OR 22.5 mg IM q6 months. With initial flare protection — anti-androgen (e.g., bicalutamide 50 mg PO daily x 4 weeks) to prevent tumor flare in patients with high disease burden.",
        ["Tumor flare in first 2-4 weeks (use anti-androgen pre-treatment)",
         "Hot flashes (~70%)",
         "Loss of libido / erectile dysfunction (~90%)",
         "Bone-mineral-density loss (DEXA monitoring + Ca/Vit-D ± antiresorptives)",
         "Cardiovascular events (modest excess; assess baseline risk)",
         "Hyperglycemia / metabolic syndrome",
         "Mood disturbance"],
        "Workhorse ADT for both mHSPC and mCRPC. Initial flare risk requires anti-androgen overlap — failure to do so can precipitate spinal cord compression in vertebral-metastasis patients.",
    )),
    ("goserelin.yaml", _drug(
        "DRUG-GOSERELIN", "Goserelin", "Гозерелін",
        ["Zoladex"], "L02AE03",
        "GnRH agonist (LHRH agonist)",
        "GnRH receptor agonist with the same flare-then-suppression mechanism as leuprolide; subcutaneous depot implant preferred at sites where IM injections are inconvenient.",
        True, True, True, True,
        "Reimbursed; common alternative to leuprolide for patient/center preference.",
        "3.6 mg SC implant monthly OR 10.8 mg SC q3 months. Same flare-protection requirement as leuprolide.",
        ["Same as leuprolide (class effect)",
         "Local injection-site reaction (depot implant)"],
        "Equivalent efficacy to leuprolide; choice often institutional or based on injection logistics.",
    )),
    ("degarelix.yaml", _drug(
        "DRUG-DEGARELIX", "Degarelix", "Дегарелікс",
        ["Firmagon"], "L02BX02",
        "GnRH antagonist (LHRH antagonist)",
        "Direct GnRH-receptor antagonist — immediate (no flare) suppression of LH/FSH and testosterone within days, vs 2-4 weeks for agonists. Preferred when rapid testosterone suppression is required (e.g., spinal cord compression risk, severe bone pain, hyperviscous metastatic burden).",
        True, True, True, False,
        "Registered but not currently NSZU-reimbursed; out-of-pocket. Verify funding pathway pre-start.",
        "Loading: 240 mg SC (two 3-mL injections) on day 1; maintenance 80 mg SC monthly.",
        ["Local injection-site reactions (~40%, more common than agonists)",
         "Hot flashes (similar to agonists)",
         "Hepatic transaminase elevations (~10%)"],
        "First-choice ADT when rapid suppression matters or when tumor flare is unacceptable. Also slightly lower CV-event risk vs LHRH agonists in some meta-analyses.",
    )),
    ("relugolix.yaml", _drug(
        "DRUG-RELUGOLIX", "Relugolix", "Релуголікс",
        ["Orgovyx"], "L02BX04",
        "GnRH antagonist (oral)",
        "Oral GnRH-receptor antagonist — first oral ADT option. Rapid testosterone suppression; cardiovascular profile favorable vs LHRH agonists in HERO trial.",
        True, True, False, False,
        "Not yet registered in Ukraine as of 2025; access only via off-label import or trials. Add to clinical-review queue for UA-availability tracking.",
        "360 mg PO loading dose day 1, then 120 mg PO once daily.",
        ["Hot flashes",
         "Diarrhea (~12%)",
         "Constipation",
         "Fatigue",
         "Same metabolic / bone class effects as injectable ADT"],
        "Best CV safety profile of any ADT in HERO trial (54% relative MACE reduction vs leuprolide). UA-access major barrier; flagged for clinician review.",
    )),
    ("abiraterone.yaml", _drug(
        "DRUG-ABIRATERONE", "Abiraterone acetate", "Абіратерон",
        ["Zytiga", "Yonsa"], "L02BX03",
        "Androgen biosynthesis inhibitor (CYP17A1)",
        "Selective irreversible CYP17A1 inhibitor — blocks adrenal and intratumoral androgen synthesis (testosterone, DHT precursors). Always combined with low-dose corticosteroid (prednisone) to mitigate mineralocorticoid excess (hypertension, hypokalemia, fluid retention).",
        True, True, True, True,
        "Reimbursed for mCRPC and high-risk mHSPC (LATITUDE-positive) per НСЗУ formulary 2024. Generic available — affordable.",
        "1000 mg PO once daily on empty stomach + prednisone 5 mg PO BID (mCRPC) or 5 mg PO daily (mHSPC). Yonsa formulation: 500 mg PO daily, food-effect mitigated.",
        ["Hypertension (~20%) — monitor BP; usually responds to standard antihypertensives",
         "Hypokalemia (~17%) — monitor K+; may require supplementation",
         "Fluid retention / peripheral edema (~25%)",
         "Hepatotoxicity (~10% transaminase elevations; monitor LFT q2w x 3 months then monthly)",
         "Cardiac events (modest excess; AF, HF)",
         "Adrenocortical insufficiency if prednisone discontinued abruptly"],
        "Workhorse ARPI for mHSPC LATITUDE-high-risk and mCRPC 1L. Always co-administer prednisone — mineralocorticoid syndrome from CYP17 blockade is serious.",
    )),
    ("enzalutamide.yaml", _drug(
        "DRUG-ENZALUTAMIDE", "Enzalutamide", "Ензалутамід",
        ["Xtandi"], "L02BB04",
        "Androgen receptor pathway inhibitor (ARPI)",
        "Direct AR antagonist — competes with androgen for binding, blocks AR nuclear translocation, DNA binding, and coactivator recruitment. Active even in low-androgen castrate environment.",
        True, True, True, True,
        "Reimbursed for mCRPC and mHSPC per НСЗУ formulary 2024.",
        "160 mg PO once daily, with or without food. Continue until progression or unacceptable toxicity.",
        ["Fatigue (~50%)",
         "Hot flashes",
         "Hypertension",
         "Falls / dizziness (~10%) — caution in elderly",
         "Cognitive impairment / memory issues (~5-10%)",
         "Seizures (~0.4%) — contraindicated in seizure-history patients",
         "Posterior reversible encephalopathy syndrome (PRES, rare)"],
        "Active in pre-chemotherapy and post-docetaxel mCRPC. CNS penetration > apalutamide / darolutamide; cognitive AEs more common in elderly.",
    )),
    ("apalutamide.yaml", _drug(
        "DRUG-APALUTAMIDE", "Apalutamide", "Апалутамід",
        ["Erleada"], "L02BB05",
        "Androgen receptor pathway inhibitor (ARPI)",
        "AR antagonist similar to enzalutamide; FDA-approved for nmCRPC (SPARTAN) and mHSPC (TITAN).",
        True, True, True, False,
        "Registered, not currently NSZU-reimbursed; out-of-pocket. Verify funding pathway pre-start.",
        "240 mg PO once daily.",
        ["Fatigue",
         "Rash (~24%) — sometimes severe; manage with topical steroids, dose hold/reduce, or discontinuation",
         "Falls / fractures (especially with concomitant ADT)",
         "Hypothyroidism (~8%) — monitor TSH",
         "Hot flashes",
         "Hypertension"],
        "Distinguishing AE from enzalutamide: rash is class-marker and notable. Fewer cognitive AEs than enzalutamide (less CNS penetration).",
    )),
    ("darolutamide.yaml", _drug(
        "DRUG-DAROLUTAMIDE", "Darolutamide", "Даролутамід",
        ["Nubeqa"], "L02BB06",
        "Androgen receptor pathway inhibitor (ARPI)",
        "AR antagonist with minimal CNS penetration (low blood-brain-barrier crossing) — favorable cognitive / fall profile vs enzalutamide. Approved for nmCRPC (ARAMIS) and mHSPC (ARASENS, in combination with docetaxel).",
        True, True, True, False,
        "Registered; reimbursement under negotiation (2025); currently out-of-pocket for most patients. Funding pathway should be confirmed pre-start.",
        "600 mg PO twice daily with food.",
        ["Fatigue (least among ARPIs)",
         "Hot flashes",
         "Skeletal pain",
         "Hypertension (modest)",
         "Liver enzyme elevations (mild)"],
        "Best safety profile of the ARPIs (no excess seizures, falls, cognitive AEs). Preferred for nmCRPC in elderly. ARASENS triplet (ADT + darolutamide + docetaxel) standard for high-volume mHSPC where infrastructure permits.",
    )),
    ("docetaxel.yaml", _drug(
        "DRUG-DOCETAXEL", "Docetaxel", "Доцетаксель",
        ["Taxotere"], "L01CD02",
        "Taxane (microtubule stabilizer)",
        "Binds β-tubulin and stabilizes microtubules, blocking mitotic spindle disassembly and inducing apoptosis. Pre-medication with corticosteroids critical to prevent fluid retention and hypersensitivity.",
        True, True, True, True,
        "Generic; reimbursed for prostate, breast, NSCLC, gastric, and other solid-tumor indications.",
        "Prostate (mHSPC + mCRPC): 75 mg/m² IV q3 weeks × 6 cycles (mHSPC) or × 10 cycles (mCRPC, until intolerance). Pre-medication: dexamethasone 8 mg PO BID × 3 days starting day before infusion.",
        ["Neutropenia (severe in 30-40%; G-CSF support if febrile-neutropenia history)",
         "Febrile neutropenia (~5-15%)",
         "Peripheral neuropathy (~30% any grade; cumulative dose-dependent)",
         "Fluid retention (~50% — pre-medication mandatory)",
         "Alopecia",
         "Mucositis",
         "Nail changes",
         "Hypersensitivity reactions (rare with pre-medication)",
         "Hepatic dysfunction may worsen toxicity — dose-modify or avoid in severe impairment"],
        "Cytotoxic backbone added to ADT for high-volume mHSPC (CHAARTED, STAMPEDE) and as ARASENS triplet partner. mCRPC option but ARPIs typically preferred 1L if no high-volume burden.",
    )),
    ("olaparib.yaml", _drug(
        "DRUG-OLAPARIB", "Olaparib", "Олапариб",
        ["Lynparza"], "L01XK01",
        "PARP inhibitor",
        "Inhibits PARP1/2 — prevents repair of single-strand DNA breaks; in HRR-deficient (BRCA1/2 + other) tumors, leads to synthetic lethality via accumulated double-strand breaks that cannot be repaired by homologous recombination.",
        True, True, True, False,
        "Registered for ovarian + breast indications with НСЗУ reimbursement; prostate indication reimbursement under negotiation. Out-of-pocket likely for prostate use until formulary update.",
        "300 mg PO BID continuous until progression or unacceptable toxicity. Dose-modify for renal impairment (CrCl 31-50 → 200 mg BID; <30 not recommended).",
        ["Anemia (~46% any grade, ~22% G3+)",
         "Fatigue (~52%)",
         "Nausea (~41%)",
         "Lymphopenia",
         "Pneumonitis (~1%) — serious; investigate any new/worsening respiratory symptoms",
         "MDS / AML (rare; long-term risk)",
         "Venous thromboembolism (modest excess in PROfound)"],
        "PROfound trial: olaparib superior to enzalutamide/abiraterone in HRR-mutant mCRPC (BRCA1/2 highest benefit). Germline + somatic HRR testing required pre-start.",
    )),
    ("talazoparib.yaml", _drug(
        "DRUG-TALAZOPARIB", "Talazoparib", "Талазопариб",
        ["Talzenna"], "L01XK04",
        "PARP inhibitor (PARP-trapper)",
        "PARP1/2 inhibitor with greater PARP-trapping activity than olaparib — physically traps PARP on DNA, enhancing cytotoxicity in HRR-deficient cells. TALAPRO-2 trial established mCRPC indication combined with enzalutamide.",
        True, True, False, False,
        "Not yet registered in Ukraine for any indication as of 2025. Access only via off-label import or trial enrollment.",
        "Combined with enzalutamide (TALAPRO-2): talazoparib 0.5 mg PO daily + enzalutamide 160 mg PO daily.",
        ["Anemia (~65% — most common dose-limiting AE; transfusion frequently required)",
         "Neutropenia",
         "Thrombocytopenia",
         "Fatigue",
         "Nausea",
         "Same MDS/AML / pneumonitis class effects as olaparib"],
        "Combination with enzalutamide for mCRPC 1L improves rPFS vs enzalutamide alone (TALAPRO-2). UA-access major barrier.",
    )),
    ("niraparib.yaml", _drug(
        "DRUG-NIRAPARIB", "Niraparib", "Нірапариб",
        ["Zejula", "Akeega (with abiraterone)"], "L01XK02",
        "PARP inhibitor",
        "PARP1/2 inhibitor with mCRPC indication in combination with abiraterone for BRCA-mutant disease (MAGNITUDE trial). Akeega is the fixed-dose combination tablet with abiraterone.",
        True, True, False, False,
        "Not currently registered in Ukraine for prostate indication. Ovarian indication may have separate access.",
        "Akeega combination: niraparib 200 mg + abiraterone 1000 mg PO daily + prednisone 10 mg daily.",
        ["Anemia (~43%)",
         "Thrombocytopenia (~36%) — distinguishing AE; dose-reduce frequently",
         "Hypertension (combination effect with abiraterone)",
         "Fatigue",
         "Nausea"],
        "BRCA-mutant mCRPC option; thrombocytopenia management more demanding than olaparib. UA-access barrier.",
    )),
    ("lutetium_177_psma.yaml", _drug(
        "DRUG-LUTETIUM-177-PSMA", "Lutetium-177 PSMA-617", "Лютецій-177 PSMA-617",
        ["Pluvicto"], "V10XX05",
        "PSMA-targeted radioligand (β-emitter)",
        "Small-molecule PSMA-binding ligand conjugated to β-emitting radionuclide Lu-177. PSMA is expressed on >90% of prostate adenocarcinoma cells; Lu-177-PSMA-617 binds PSMA and delivers cytotoxic β-radiation directly to tumor sites. Requires PSMA-PET-positive disease for selection (VISION criteria).",
        True, True, False, False,
        "Not registered in Ukraine; closest access via international referral (EU centers). Major access barrier — flagged for clinical-review queue.",
        "7.4 GBq IV q6 weeks × 6 cycles (VISION protocol). Administered in nuclear medicine / radioligand therapy unit with appropriate radiation safety.",
        ["Dry mouth / xerostomia (most common AE — affects salivary gland uptake)",
         "Fatigue",
         "Anemia",
         "Thrombocytopenia (~10% G3+)",
         "Renal effects (long-term; monitor CrCl)",
         "Bone marrow suppression cumulative — discontinue if persistent G3+"],
        "VISION trial: significant rPFS + OS benefit in PSMA-PET-positive mCRPC post-ARPI + post-taxane. Requires nuclear medicine infrastructure + PSMA-PET availability — limits access in Ukraine to a few centers.",
    )),
    ("radium_223.yaml", _drug(
        "DRUG-RADIUM-223", "Radium-223 dichloride", "Радій-223 дихлорид",
        ["Xofigo"], "V10XX03",
        "Bone-seeking α-emitter",
        "Calcium-mimetic α-emitter that incorporates into hydroxyapatite at sites of high bone turnover (osteoblastic metastases). α-radiation has ~100 µm range — high local tumor cell kill with minimal marrow toxicity vs β-emitters.",
        True, True, False, False,
        "Not registered in Ukraine. Access via international referral.",
        "55 kBq/kg IV q4 weeks × 6 cycles. Symptomatic bone-predominant mCRPC without visceral metastases (visceral mets exclude — ALSYMPCA exclusion criterion).",
        ["Anemia",
         "Diarrhea",
         "Bone pain (transient flare)",
         "Falls (population is fragile)",
         "Avoid concurrent abiraterone + prednisone — ERA-223 trial showed excess fractures and deaths"],
        "ALSYMPCA: OS benefit + symptomatic skeletal-event reduction in bone-predominant mCRPC. ERA-223 caution: avoid combination with abiraterone (use sequentially). UA-access barrier.",
    )),
    ("denosumab.yaml", _drug(
        "DRUG-DENOSUMAB", "Denosumab", "Деносумаб",
        ["Xgeva (oncology)", "Prolia (osteoporosis)"], "M05BX04",
        "RANKL inhibitor (monoclonal antibody)",
        "Fully human monoclonal antibody targeting RANKL, blocking osteoclast formation, function, and survival. Reduces skeletal-related events (SREs) in bone-metastatic prostate, breast, and other solid tumors.",
        True, True, True, True,
        "Reimbursed for cancer bone-metastasis prophylaxis (Xgeva indication); osteoporosis indication separate. Cancer dosing covered.",
        "Bone-metastasis prophylaxis: 120 mg SC q4 weeks. Always combine with calcium 500-1000 mg/day + vitamin D 400-800 IU/day.",
        ["Hypocalcemia (severe risk if Ca/Vit-D not co-administered)",
         "Osteonecrosis of the jaw (ONJ, ~2-5% — pre-treatment dental evaluation; avoid invasive dental procedures during treatment)",
         "Atypical femur fractures (rare, long-term)",
         "Hypophosphatemia",
         "Rebound vertebral fractures if abruptly stopped after long use",
         "No renal-dose adjustment required (vs zoledronate)"],
        "Preferred over zoledronate in patients with renal impairment. Cancer bone-metastasis dosing distinct from osteoporosis dosing — keep separate. Pre-treatment dental clearance critical to reduce ONJ risk.",
    )),
]


# ── 4. Biomarkers (5 prostate-specific) ──────────────────────────────


BIOMARKERS: list[tuple[str, str]] = [
    ("bio_psa.yaml", """\
id: BIO-PSA
names:
  preferred: "Prostate-specific antigen (PSA)"
  ukrainian: "Простатичний специфічний антиген (ПСА)"
  english: "Prostate-specific antigen"
  abbreviations: ["PSA"]
codes:
  loinc: "2857-1"

biomarker_type: serum_marker

measurement:
  method: "Immunoassay (ECLIA, CLIA)"
  units: "ng/mL"
  typical_range: [0, 1000]

interpretation_notes: >
  Disease-specific cutoffs:
  • Screening / surveillance >4 ng/mL → biopsy consideration (varies with age)
  • mHSPC: PSA >20 with metastatic disease defines high-risk LATITUDE
  • PSA doubling time <6 months on ADT defines aggressive nmCRPC
  • PSA progression on castration: ≥25% increase + ≥2 ng/mL absolute, confirmed 3+ weeks later

related_biomarkers: []

last_reviewed: null
notes: >
  Workhorse serum biomarker for prostate. Disease-state stratification
  (mHSPC vs mCRPC vs nmCRPC) and CHAARTED/LATITUDE risk classification
  rely heavily on PSA dynamics + cross-reference with imaging.
"""),
    ("bio_psma_pet.yaml", """\
id: BIO-PSMA-PET
names:
  preferred: "PSMA-PET imaging avidity"
  ukrainian: "ПСМА-ПЕТ-авідність"
  english: "PSMA-PET imaging avidity"
  abbreviations: ["PSMA-PET"]
codes:
  loinc: null

biomarker_type: protein_expression_imaging

measurement:
  method: "Ga-68-PSMA-11 OR F-18-PSMA-1007 PET/CT"
  units: "qualitative (positive / negative) per VISION criteria"
  typical_range: null

interpretation_notes: >
  VISION criteria for Lu-177-PSMA eligibility: at least one PSMA-positive
  metastatic lesion AND no PSMA-negative lesions exceeding the size of the
  PSMA-positive lesions on the same scan. Threshold uptake: greater than
  liver mediastinal blood pool.

related_biomarkers: []

last_reviewed: null
notes: >
  Drives Lu-PSMA selection. Requires nuclear medicine infrastructure.
  In Ukraine PSMA-PET availability concentrated in 2-3 academic centers
  (Kyiv, Dnipro). Access barrier.
"""),
    ("bio_brca_germline.yaml", """\
id: BIO-BRCA-GERMLINE
names:
  preferred: "Germline BRCA1/2 mutation status"
  ukrainian: "Гермінальний статус мутацій BRCA1/2"
  english: "Germline BRCA1/2 mutation status"
codes:
  loinc: "94075-3"

biomarker_type: mutation
mutation_details:
  gene: "BRCA1, BRCA2"
  inheritance: germline
  type: "various pathogenic / likely-pathogenic variants"
  functional_impact: "loss-of-function (HRR pathway)"

measurement:
  method: "NGS panel (germline) with Sanger confirmation of variants of interest"
  sensitivity_requirement: "Pathogenic variants captured per ACMG variant-classification standards"

interpretation_notes: >
  Pathogenic / likely-pathogenic germline BRCA1 or BRCA2 variant. Confers:
  • PARPi indication (olaparib, talazoparib, niraparib) in mCRPC
  • Aggressive natural history — earlier metastasis, shorter response durations
  • Cascade-testing recommendation for first-degree relatives

related_biomarkers: ["BIO-HRR-PANEL"]

last_reviewed: null
notes: >
  Germline testing should be offered to all metastatic prostate patients
  per NCCN 2025 (regardless of family history). Cascade testing important
  for relatives. Germline + tumor (somatic) testing complementary.
"""),
    ("bio_hrr_panel.yaml", """\
id: BIO-HRR-PANEL
names:
  preferred: "Homologous recombination repair (HRR) gene panel status"
  ukrainian: "Панель генів гомологічної рекомбінаційної репарації (HRR)"
  english: "HRR gene panel status"
  abbreviations: ["HRR-mutant"]
codes:
  loinc: null

biomarker_type: mutation
mutation_details:
  genes: ["BRCA1", "BRCA2", "ATM", "BARD1", "BRIP1", "CDK12", "CHEK1", "CHEK2", "FANCL", "PALB2", "RAD51B", "RAD51C", "RAD51D", "RAD54L"]
  inheritance: "germline OR somatic"
  type: "loss-of-function variants"

measurement:
  method: "Tumor-tissue NGS panel (somatic) OR ctDNA OR germline NGS"
  sensitivity_requirement: "VAF detection threshold ≥5% recommended for ctDNA"

interpretation_notes: >
  Any pathogenic alteration in HRR pathway genes. PROfound trial defined
  Cohort A (BRCA1/2 + ATM) where olaparib benefit was largest, vs Cohort B
  (other HRR genes) where benefit was smaller but still positive. NCCN
  recommends testing all metastatic patients.

related_biomarkers: ["BIO-BRCA-GERMLINE"]

last_reviewed: null
notes: >
  Combined germline + somatic testing yields ~25% HRR-positivity in mCRPC.
  PARPi benefit greatest in BRCA1/2 (higher rPFS HR). Test infrastructure
  in UA major bottleneck — flagged for clinician review.
"""),
    ("bio_gleason_isup.yaml", """\
id: BIO-GLEASON-ISUP
names:
  preferred: "Gleason score / ISUP grade group"
  ukrainian: "Бал Глісона / ISUP grade group"
  english: "Gleason score / ISUP grade group"
codes:
  loinc: null

biomarker_type: pathology_grading

measurement:
  method: "Histopathology of biopsy / RP specimen"
  units: "Gleason 6-10 / ISUP 1-5"
  typical_range: [6, 10]

interpretation_notes: >
  ISUP grade groups (modern):
  • Grade 1 (Gleason 3+3=6): low-risk
  • Grade 2 (Gleason 3+4=7): favorable intermediate
  • Grade 3 (Gleason 4+3=7): unfavorable intermediate
  • Grade 4 (Gleason 4+4 / 3+5 / 5+3 = 8): high
  • Grade 5 (Gleason 9-10): very-high

  In mHSPC, Gleason ≥8 is one of the LATITUDE high-risk criteria.

related_biomarkers: []

last_reviewed: null
notes: >
  Universal pathology-grading framework. WHO 2022 endorses ISUP grade
  group nomenclature; older Gleason notation still common in clinical
  reports.
"""),
]


# ── 5. Tests (6 prostate-specific) ────────────────────────────────────


TESTS: list[tuple[str, str]] = [
    ("test_psa_serum.yaml", """\
id: TEST-PSA-SERUM
names:
  preferred: "Serum PSA"
  ukrainian: "Сироватковий ПСА"
test_type: serum
priority_class: critical
specimen: "Serum (gold-top or red-top tube)"
turnaround_hours_typical: 24
measures: ["BIO-PSA"]
sources: [SRC-NCCN-PROSTATE-2025, SRC-EAU-PROSTATE-2024]
last_reviewed: null
notes: >
  Baseline + serial PSA dynamics drive disease-state classification
  (mHSPC vs mCRPC vs nmCRPC) and treatment-response assessment.
  Calculate doubling time when ≥3 measurements over ≥8 weeks available.
"""),
    ("test_psma_pet.yaml", """\
id: TEST-PSMA-PET
names:
  preferred: "PSMA-PET/CT (Ga-68 or F-18)"
  ukrainian: "ПСМА-ПЕТ/КТ"
test_type: imaging_pet
priority_class: standard
specimen: "Whole-body PSMA-targeted radiotracer"
turnaround_hours_typical: 48
measures: ["BIO-PSMA-PET"]
sources: [SRC-NCCN-PROSTATE-2025, SRC-EAU-PROSTATE-2024]
last_reviewed: null
notes: >
  Required for Lu-PSMA eligibility per VISION criteria. Also superior
  to conventional CT + bone scan for staging and recurrence detection.
  UA availability limited to 2-3 centers; document referral pathway.
"""),
    ("test_bone_scan.yaml", """\
id: TEST-BONE-SCAN
names:
  preferred: "Whole-body Tc-99m MDP bone scintigraphy"
  ukrainian: "Сцинтиграфія кісток (Tc-99m MDP)"
test_type: imaging_nm
priority_class: standard
specimen: "IV Tc-99m MDP, whole-body imaging"
turnaround_hours_typical: 24
measures: []
sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  Baseline staging + on-treatment monitoring for skeletal disease.
  Less sensitive than PSMA-PET but more universally available in Ukraine.
"""),
    ("test_germline_brca_panel.yaml", """\
id: TEST-GERMLINE-BRCA-PANEL
names:
  preferred: "Germline BRCA1/2 + HRR panel sequencing"
  ukrainian: "Гермінальне секвенування BRCA1/2 + HRR панель"
test_type: molecular_germline
priority_class: standard
specimen: "Peripheral blood OR buccal swab"
turnaround_hours_typical: 504
measures: ["BIO-BRCA-GERMLINE", "BIO-HRR-PANEL"]
sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  Recommend for ALL metastatic patients per NCCN 2025. Genetic-counseling
  consent required pre-test. UA availability concentrated in private labs;
  add to clinical-review queue for funding pathway tracking.
"""),
    ("test_somatic_hrr_panel.yaml", """\
id: TEST-SOMATIC-HRR-PANEL
names:
  preferred: "Tumor-tissue (or ctDNA) HRR-pathway NGS panel"
  ukrainian: "Тканинна (або ctDNA) HRR-панель NGS"
test_type: molecular_somatic
priority_class: standard
specimen: "FFPE tumor block (preferred) OR plasma for ctDNA"
turnaround_hours_typical: 504
measures: ["BIO-HRR-PANEL"]
sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  PROfound trial used tumor-tissue NGS. ctDNA acceptable when tissue
  unavailable / inadequate. Required for PARPi indication. UA-availability
  major access barrier.
"""),
    ("test_testosterone_serum.yaml", """\
id: TEST-TESTOSTERONE-SERUM
names:
  preferred: "Serum total testosterone"
  ukrainian: "Сироватковий тестостерон"
test_type: serum
priority_class: standard
specimen: "Serum, morning sample preferred"
turnaround_hours_typical: 24
measures: []
sources: [SRC-NCCN-PROSTATE-2025, SRC-EAU-PROSTATE-2024]
last_reviewed: null
notes: >
  Castrate level <50 ng/dL (~1.7 nmol/L) defines castration status —
  prerequisite for mCRPC vs mHSPC classification. Also confirms ADT
  pharmacodynamic effect at month 1-2 post-initiation.
"""),
]


# ── 6. Workup (1) ──────────────────────────────────────────────────────


WORKUP = """\
id: WORKUP-METASTATIC-PROSTATE
applicable_to:
  lineage_hints:
    - solid_tumor_prostate
    - prostate_cancer_metastatic
  tissue_locations:
    - prostate
    - bone
    - lymph_nodes_pelvic
  presentation_keywords:
    - prostate_cancer_metastatic
    - rising_psa
    - bone_metastases
    - mhspc
    - mcrpc

required_tests:
  - TEST-PSA-SERUM
  - TEST-TESTOSTERONE-SERUM
  - TEST-BONE-SCAN
  - TEST-GERMLINE-BRCA-PANEL

desired_tests:
  - TEST-PSMA-PET
  - TEST-SOMATIC-HRR-PANEL
  - TEST-CECT-CAP

triggers_mdt_roles:
  required:
    - medical_oncologist
    - urologist
  recommended:
    - nuclear_medicine_specialist
    - molecular_geneticist
  rationale_per_role:
    medical_oncologist: "Systemic therapy planning for mHSPC/mCRPC."
    urologist: "Local control + ADT initiation; surgical history input."
    nuclear_medicine_specialist: "PSMA-PET interpretation + Lu-PSMA candidacy assessment."
    molecular_geneticist: "Germline + somatic HRR testing for PARPi indication."

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024, SRC-EAU-PROSTATE-2024]

last_reviewed: null
notes: >
  Modern staging integrates PSMA-PET when available — significantly
  upstages disease vs conventional CT + bone scan. Germline + somatic
  HRR testing now routine per NCCN 2025 for all metastatic patients.
"""


# ── 7. Regimens (7) ───────────────────────────────────────────────────


REGIMENS: list[tuple[str, str]] = [
    ("reg_adt_leuprolide.yaml", """\
id: REG-ADT-LEUPROLIDE
name: "ADT — leuprolide depot (continuous)"
name_ua: "АДТ — лейпрорелін депо (безперервно)"
alternate_names: ["LHRH agonist monotherapy", "Leuprolide ADT"]

components:
  - drug_id: DRUG-LEUPROLIDE
    dose: "11.25 mg IM q3 months (or 22.5 mg q6 months)"
    schedule: "Continuous from initiation"
    route: IM

cycle_length_days: 90
total_cycles: "Continuous until disease progression to CRPC"
toxicity_profile: low-moderate

premedication:
  - "Bicalutamide 50 mg PO daily x 2-4 weeks at initiation if high-volume disease (anti-androgen flare protection)"
mandatory_supportive_care:
  - SUP-BONE-HEALTH-PROSTATE
monitoring_schedule_id: null

dose_adjustments: []

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: true
  notes: "ADT backbone — НСЗУ-reimbursed."

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  Backbone for hormone-sensitive disease. Almost always combined with
  ARPI (abiraterone, enzalutamide, apalutamide, darolutamide) — ADT-mono
  is the older standard of care, now reserved for patients unable to
  tolerate ARPI addition.
"""),
    ("reg_adt_abiraterone.yaml", """\
id: REG-ADT-ABIRATERONE
name: "ADT + abiraterone + prednisone (continuous)"
name_ua: "АДТ + абіратерон + преднізолон (безперервно)"
alternate_names: ["LATITUDE regimen (mHSPC)", "COU-AA-302 regimen (mCRPC)"]

components:
  - drug_id: DRUG-LEUPROLIDE
    dose: "11.25 mg IM q3 months"
    schedule: "Continuous from initiation"
    route: IM
  - drug_id: DRUG-ABIRATERONE
    dose: "1000 mg PO daily on empty stomach"
    schedule: "Continuous"
    route: PO
  - drug_id: DRUG-PREDNISONE
    dose: "5 mg PO BID (mCRPC) OR 5 mg PO daily (mHSPC)"
    schedule: "Continuous with abiraterone"
    route: PO

cycle_length_days: 28
total_cycles: "Continuous until progression or unacceptable toxicity"
toxicity_profile: moderate

premedication: []
mandatory_supportive_care:
  - SUP-BONE-HEALTH-PROSTATE
monitoring_schedule_id: null

dose_adjustments:
  - condition: "Severe hepatic impairment (Child-Pugh C)"
    modification: "Avoid abiraterone"
  - condition: "Hypokalemia or fluid retention"
    modification: "Increase prednisone dose, add antihypertensive / K+ supplement"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: true
  notes: "Generic abiraterone widely available; reimbursed for mHSPC + mCRPC."

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  LATITUDE: ADT + abiraterone superior to ADT alone in high-risk mHSPC.
  COU-AA-302 / COU-AA-301: established in chemo-naive and post-chemo
  mCRPC. Always with prednisone — NEVER alone (mineralocorticoid syndrome).

  Cross-disease use: same regimen reused for mCRPC 1L and high-risk mHSPC.
"""),
    ("reg_adt_enzalutamide.yaml", """\
id: REG-ADT-ENZALUTAMIDE
name: "ADT + enzalutamide (continuous)"
name_ua: "АДТ + ензалутамід (безперервно)"
alternate_names: ["ENZAMET-style", "PREVAIL regimen", "AFFIRM regimen"]

components:
  - drug_id: DRUG-LEUPROLIDE
    dose: "11.25 mg IM q3 months"
    schedule: "Continuous"
    route: IM
  - drug_id: DRUG-ENZALUTAMIDE
    dose: "160 mg PO daily"
    schedule: "Continuous"
    route: PO

cycle_length_days: 28
total_cycles: "Continuous until progression or unacceptable toxicity"
toxicity_profile: low-moderate

premedication: []
mandatory_supportive_care:
  - SUP-BONE-HEALTH-PROSTATE
monitoring_schedule_id: null

dose_adjustments:
  - condition: "History of seizures"
    modification: "Avoid enzalutamide (alternative: apalutamide / darolutamide)"
  - condition: "Severe hepatic impairment (Child-Pugh C)"
    modification: "Reduce to 80 mg PO daily"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: true
  notes: "Reimbursed for mHSPC + mCRPC."

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  ENZAMET established benefit in mHSPC. PREVAIL: 1L mCRPC vs ADT-mono.
  AFFIRM: post-docetaxel mCRPC. Most CNS penetration of ARPIs — cognitive
  AEs more common in elderly.
"""),
    ("reg_adt_darolutamide_docetaxel.yaml", """\
id: REG-ADT-DAROLUTAMIDE-DOCETAXEL
name: "ADT + darolutamide + docetaxel (ARASENS triplet)"
name_ua: "АДТ + даролутамід + доцетаксель (ARASENS трипл)"
alternate_names: ["ARASENS triplet", "Triplet therapy mHSPC"]

components:
  - drug_id: DRUG-LEUPROLIDE
    dose: "11.25 mg IM q3 months"
    schedule: "Continuous"
    route: IM
  - drug_id: DRUG-DAROLUTAMIDE
    dose: "600 mg PO BID with food"
    schedule: "Continuous"
    route: PO
  - drug_id: DRUG-DOCETAXEL
    dose: "75 mg/m² IV q3 weeks"
    schedule: "Cycles 1-6 (then ADT + darolutamide continue)"
    route: IV

cycle_length_days: 21
total_cycles: "Docetaxel × 6; ADT + darolutamide continuous until progression"
toxicity_profile: moderate-severe

premedication:
  - "Dexamethasone 8 mg PO BID x 3 days starting day before docetaxel"
mandatory_supportive_care:
  - SUP-BONE-HEALTH-PROSTATE
  - SUP-G-CSF-PRIMARY-PROPHYLAXIS-PROSTATE
monitoring_schedule_id: null

dose_adjustments:
  - condition: "Febrile neutropenia"
    modification: "G-CSF support; consider docetaxel dose reduction to 60-65 mg/m² subsequent cycles"
  - condition: "Peripheral neuropathy ≥G2"
    modification: "Hold docetaxel; reduce to 60 mg/m² when ≤G1"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: false
  notes: "Darolutamide registered but reimbursement under negotiation 2025; out-of-pocket for most patients. Docetaxel + leuprolide reimbursed."

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  ARASENS: significant OS benefit for triplet vs ADT + docetaxel in
  high-volume mHSPC. Requires docetaxel-eligible patient (ECOG 0-1,
  no significant comorbidity). UA-access constrained by darolutamide
  reimbursement gap — flagged for clinical-review queue.
"""),
    ("reg_olaparib_mono.yaml", """\
id: REG-OLAPARIB-MONO
name: "Olaparib monotherapy (mCRPC, HRR-mutant)"
name_ua: "Олапариб монотерапія (мКРРПЗ, HRR-мутант)"
alternate_names: ["PROfound regimen"]

components:
  - drug_id: DRUG-OLAPARIB
    dose: "300 mg PO BID continuous"
    schedule: "Until progression or unacceptable toxicity"
    route: PO

cycle_length_days: 28
total_cycles: "Continuous until progression"
toxicity_profile: moderate

premedication: []
mandatory_supportive_care:
  - SUP-BONE-HEALTH-PROSTATE
monitoring_schedule_id: null

dose_adjustments:
  - condition: "CrCl 31-50 mL/min"
    modification: "Reduce to 200 mg PO BID"
  - condition: "CrCl <30 mL/min"
    modification: "Avoid"
  - condition: "Anemia ≥G2"
    modification: "Hold; reduce to 250 mg → 200 mg BID stepwise"
  - condition: "New respiratory symptoms"
    modification: "Hold; rule out pneumonitis"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: false
  notes: "Registered for ovarian/breast indications; prostate reimbursement under negotiation. Out-of-pocket for prostate use until formulary update."

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  PROfound: olaparib superior to enzalutamide / abiraterone in HRR-mutant
  mCRPC post-ARPI. BRCA1/2 cohort largest benefit. Requires germline +/-
  somatic HRR testing pre-start.
"""),
    ("reg_lutetium_psma.yaml", """\
id: REG-LUTETIUM-PSMA
name: "Lutetium-177 PSMA-617 radioligand therapy"
name_ua: "Лютецій-177 PSMA-617 радіолігандна терапія"
alternate_names: ["Pluvicto", "VISION regimen"]

components:
  - drug_id: DRUG-LUTETIUM-177-PSMA
    dose: "7.4 GBq IV"
    schedule: "q6 weeks × 6 cycles"
    route: IV

cycle_length_days: 42
total_cycles: "6 (extend to 8 if responding and tolerated, per protocol)"
toxicity_profile: moderate

premedication:
  - "Hydration pre + post infusion"
  - "Dental evaluation pre-start (xerostomia mitigation)"
mandatory_supportive_care:
  - SUP-BONE-HEALTH-PROSTATE
monitoring_schedule_id: null

dose_adjustments:
  - condition: "Persistent G3+ bone marrow suppression"
    modification: "Discontinue"
  - condition: "Renal function decline (CrCl <50)"
    modification: "Reduce dose or discontinue"

ukraine_availability:
  all_components_registered: false
  all_components_reimbursed: false
  notes: "Not registered in Ukraine. Access via international referral (EU centers — Germany, Czech Republic). Major access barrier; flagged for clinical-review queue."

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  VISION trial: significant rPFS + OS benefit in PSMA-PET-positive mCRPC
  post-ARPI + post-taxane. Requires nuclear medicine infrastructure +
  PSMA-PET. UA access concentrated in 2-3 academic centers.
"""),
    ("reg_adt_apalutamide.yaml", """\
id: REG-ADT-APALUTAMIDE
name: "ADT + apalutamide (continuous)"
name_ua: "АДТ + апалутамід (безперервно)"
alternate_names: ["TITAN-style (mHSPC)", "SPARTAN-style (nmCRPC)"]

components:
  - drug_id: DRUG-LEUPROLIDE
    dose: "11.25 mg IM q3 months"
    schedule: "Continuous"
    route: IM
  - drug_id: DRUG-APALUTAMIDE
    dose: "240 mg PO daily"
    schedule: "Continuous"
    route: PO

cycle_length_days: 28
total_cycles: "Continuous until progression"
toxicity_profile: low-moderate

premedication: []
mandatory_supportive_care:
  - SUP-BONE-HEALTH-PROSTATE
monitoring_schedule_id: null

dose_adjustments:
  - condition: "G3+ rash"
    modification: "Hold; resume at 180 mg or 120 mg after resolution"
  - condition: "Hypothyroidism"
    modification: "Levothyroxine; continue apalutamide"

ukraine_availability:
  all_components_registered: true
  all_components_reimbursed: false
  notes: "Apalutamide registered but not currently NSZU-reimbursed; out-of-pocket. Verify funding pathway pre-start."

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  TITAN: mHSPC benefit. SPARTAN: nmCRPC benefit. Distinguishing AE: rash
  (~24%); hypothyroidism (~8%) — monitor TSH. Less CNS penetration than
  enzalutamide.
"""),
]


# ── 8. RedFlags (5) ───────────────────────────────────────────────────


REDFLAGS: list[tuple[str, str]] = [
    ("rf_prostate_organ_dysfunction.yaml", """\
id: RF-PROSTATE-ORGAN-DYSFUNCTION
definition: "Renal dysfunction (CrCl <50 mL/min) or severe hepatic impairment (Child-Pugh C) — limits PARPi (olaparib renal-cleared) and ARPI (abiraterone hepatic) dosing."
definition_ua: "Ниркова дисфункція (CrCl <50 мл/хв) або тяжке печінкове порушення (Child-Pugh C) — обмежує PARPi (олапариб нирковий) і ARPI (абіратерон печінковий) дозування."

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

relevant_diseases: [DIS-PROSTATE]
shifts_algorithm: []

sources:
  - SRC-NCCN-PROSTATE-2025
  - SRC-ESMO-PROSTATE-2024

last_reviewed: null
draft: false

notes: >
  Olaparib requires CrCl ≥31 (with dose-mod) for safe use; <30 avoid.
  Abiraterone Child-Pugh C: avoid. Surfaces in MDT as need for renal/
  hepatic input.
"""),
    ("rf_prostate_infection_screening.yaml", """\
id: RF-PROSTATE-INFECTION-SCREENING
definition: "Pre-treatment HBV/HCV/HIV serology + dental evaluation (denosumab/zoledronate ONJ risk; lutetium-PSMA xerostomia) standard for mCRPC initiation."
definition_ua: "Скринінг HBV/HCV/HIV перед початком лікування + стоматологічна оцінка (ризик ONJ при деносумабі/золедронаті; ксеростомія при лютецій-PSMA) — стандарт перед початком mCRPC."

trigger:
  type: composite_clinical
  any_of:
    - finding: "dental_clearance_pending"
      value: true
    - finding: "hbsag"
      value: "positive"

clinical_direction: investigate
severity: minor
priority: 100
category: infection-screening

relevant_diseases: [DIS-PROSTATE]
shifts_algorithm: []

sources:
  - SRC-NCCN-PROSTATE-2025
  - SRC-ESMO-PROSTATE-2024

last_reviewed: null
draft: false

notes: >
  Cross-disease HBV reactivation handled by RF-UNIVERSAL-HBV-REACTIVATION-
  RISK. Dental clearance pre-bone-modifying-agent unique to bone-meta
  diseases (prostate, breast, MM).
"""),
    ("rf_prostate_high_risk_biology.yaml", """\
id: RF-PROSTATE-HIGH-RISK-BIOLOGY
definition: "Germline or somatic BRCA1/2 mutation OR broader HRR pathway alteration (ATM, CDK12, PALB2, etc.) — predicts PARPi response; opens olaparib/talazoparib indication in mCRPC."
definition_ua: "Гермінальна або соматична мутація BRCA1/2 АБО ширша HRR-альтерація (ATM, CDK12, PALB2 та ін.) — передбачає відповідь на PARPi; відкриває олапариб/талазопариб для мКРРПЗ."

trigger:
  type: biomarker
  any_of:
    - finding: "BIO-BRCA-GERMLINE"
      value: "positive"
    - finding: "BIO-HRR-PANEL"
      value: "positive"
    - finding: "brca1_mutation"
      value: true
    - finding: "brca2_mutation"
      value: true
    - finding: "hrr_pathway_mutation"
      value: true

clinical_direction: intensify
severity: major
priority: 100
category: high-risk-biology

relevant_diseases: [DIS-PROSTATE]
shifts_algorithm: [ALGO-PROSTATE-MCRPC-1L]

sources:
  - SRC-NCCN-PROSTATE-2025
  - SRC-ESMO-PROSTATE-2024

last_reviewed: null
draft: false

notes: >
  PROfound (olaparib) + TALAPRO-2 (talazoparib + enzalutamide) +
  MAGNITUDE (niraparib + abiraterone) define PARPi indications. BRCA1/2
  largest benefit; broader HRR cohort smaller but positive. Germline +
  somatic testing recommended for ALL metastatic patients per NCCN 2025.
"""),
    ("rf_prostate_transformation_progression.yaml", """\
id: RF-PROSTATE-TRANSFORMATION-PROGRESSION
definition: "Spinal cord compression OR rapid PSA doubling time (<3 months) OR new visceral metastases — emergency or aggressive-progression flag requiring urgent intervention or treatment intensification."
definition_ua: "Компресія спинного мозку АБО швидке подвоєння ПСА (<3 міс) АБО нові вісцеральні метастази — невідкладний або агресивно-прогресуючий тригер, що потребує термінового втручання або інтенсифікації."

trigger:
  type: composite_clinical
  any_of:
    - finding: "spinal_cord_compression"
      value: true
    - finding: "psa_doubling_time_months"
      threshold: 3
      comparator: "<"
    - finding: "new_visceral_metastases"
      value: true

clinical_direction: hold
severity: critical
priority: 50
category: transformation-progression

relevant_diseases: [DIS-PROSTATE]
shifts_algorithm: []

sources:
  - SRC-NCCN-PROSTATE-2025
  - SRC-ESMO-PROSTATE-2024

last_reviewed: null
draft: false

notes: >
  Spinal cord compression: emergent neurosurgical / RT consult AND
  immediate testosterone suppression (degarelix preferred for speed
  vs LHRH agonists). PSA doubling time <3 months in nmCRPC: criterion
  for ARPI initiation per NCCN. Visceral mets in mCRPC: docetaxel or
  cabazitaxel preferred over additional ARPI (cross-resistance).
  Direction `hold` reflects priority — emergent care precedes scheduled
  systemic therapy decisions.
"""),
    ("rf_prostate_frailty_age.yaml", """\
id: RF-PROSTATE-FRAILTY-AGE
definition: "Age ≥80 OR ECOG ≥3 with significant comorbidity — docetaxel poorly tolerated; ARPI monotherapy preferred; consider darolutamide for cognitive-AE-sensitive patients."
definition_ua: "Вік ≥80 АБО ECOG ≥3 із суттєвими коморбідностями — доцетаксель погано переноситься; ARPI монотерапія краща; даролутамід для пацієнтів, чутливих до когнітивних AE."

trigger:
  type: composite_clinical
  any_of:
    - finding: "age_years"
      threshold: 80
      comparator: ">="
    - all_of:
        - finding: "ecog_status"
          threshold: 3
          comparator: ">="
        - finding: "comorbidity_count"
          threshold: 2
          comparator: ">="

clinical_direction: de-escalate
severity: major
priority: 100
category: frailty-age

relevant_diseases: [DIS-PROSTATE]
shifts_algorithm: [ALGO-PROSTATE-MHSPC-1L]

sources:
  - SRC-NCCN-PROSTATE-2025
  - SRC-ESMO-PROSTATE-2024

last_reviewed: null
draft: false

notes: >
  Triplet (ARASENS) carries significant docetaxel toxicity unsuitable
  for fragile elderly. ARPI monotherapy preserves OS benefit with
  tolerable AEs. Darolutamide preferred when cognitive AEs / falls
  are particularly concerning.
"""),
]


# ── 9. Indications (5) ───────────────────────────────────────────────


INDICATIONS: list[tuple[str, str]] = [
    ("ind_prostate_mhspc_1l_arpi_doublet.yaml", """\
id: IND-PROSTATE-MHSPC-1L-ARPI-DOUBLET
plan_track: standard

applicable_to:
  disease_id: DIS-PROSTATE
  disease_state: mHSPC
  line_of_therapy: 1
  stage_requirements: ["IV"]
  biomarker_requirements_required: []
  biomarker_requirements_excluded: []
  demographic_constraints:
    ecog_max: 2

recommended_regimen: REG-ADT-ABIRATERONE
concurrent_therapy: []
followed_by: []

evidence_level: high
strength_of_recommendation: strong
nccn_category: "1"

expected_outcomes:
  overall_response_rate: "PSA decline ≥90% in ~75-80% within 6 months"
  median_radiographic_pfs_months: 33
  median_overall_survival_months: 53
  notes: "LATITUDE high-risk subgroup OS benefit pronounced; ENZAMET / TITAN show similar OS-trends with enzalutamide / apalutamide"

hard_contraindications: []
red_flags_triggering_alternative:
  - RF-PROSTATE-HIGH-RISK-BIOLOGY
required_tests:
  - TEST-PSA-SERUM
  - TEST-TESTOSTERONE-SERUM
  - TEST-BONE-SCAN
  - TEST-GERMLINE-BRCA-PANEL
desired_tests:
  - TEST-PSMA-PET
  - TEST-SOMATIC-HRR-PANEL

sources:
  - source_id: SRC-NCCN-PROSTATE-2025
    weight: primary
  - source_id: SRC-ESMO-PROSTATE-2024
    weight: primary

last_reviewed: null
reviewers: []

notes: >
  Default for low/intermediate-volume mHSPC. Triplet (ARASENS) reserved
  for high-volume CHAARTED criteria with docetaxel-eligible patient.
  Enzalutamide / apalutamide acceptable substitutes for abiraterone
  in patient-specific contexts (e.g., diabetes / steroid-avoidance
  preference favors enza / apalu over abi).
"""),
    ("ind_prostate_mhspc_1l_triplet.yaml", """\
id: IND-PROSTATE-MHSPC-1L-TRIPLET
plan_track: aggressive

applicable_to:
  disease_id: DIS-PROSTATE
  disease_state: mHSPC
  line_of_therapy: 1
  stage_requirements: ["IV"]
  biomarker_requirements_required: []
  biomarker_requirements_excluded: []
  demographic_constraints:
    ecog_max: 1

recommended_regimen: REG-ADT-DAROLUTAMIDE-DOCETAXEL
concurrent_therapy: []
followed_by: []

evidence_level: high
strength_of_recommendation: strong
nccn_category: "1"

expected_outcomes:
  overall_response_rate: "PSA <0.2 ng/mL at 9 months in ~55-65%"
  median_radiographic_pfs_months: 36
  median_overall_survival_months: "Not yet reached (ARASENS final analysis pending)"
  hr_overall_survival: "0.68"

hard_contraindications: []
red_flags_triggering_alternative:
  - RF-PROSTATE-FRAILTY-AGE
required_tests:
  - TEST-PSA-SERUM
  - TEST-TESTOSTERONE-SERUM
  - TEST-BONE-SCAN
  - TEST-GERMLINE-BRCA-PANEL
desired_tests:
  - TEST-PSMA-PET
  - TEST-SOMATIC-HRR-PANEL

sources:
  - source_id: SRC-NCCN-PROSTATE-2025
    weight: primary
  - source_id: SRC-ESMO-PROSTATE-2024
    weight: primary

last_reviewed: null
reviewers: []

notes: >
  ARASENS (darolutamide + docetaxel + ADT): OS benefit in high-volume
  mHSPC. Requires docetaxel-eligible patient. Alternative formulations:
  ADT + abiraterone + docetaxel (PEACE-1) for centers without
  darolutamide access.
"""),
    ("ind_prostate_mcrpc_1l_arpi.yaml", """\
id: IND-PROSTATE-MCRPC-1L-ARPI
plan_track: standard

applicable_to:
  disease_id: DIS-PROSTATE
  disease_state: mCRPC
  line_of_therapy: 1
  stage_requirements: ["IV"]
  biomarker_requirements_required: []
  biomarker_requirements_excluded:
    - biomarker_id: BIO-HRR-PANEL
      value_constraint: "negative"
      required: false
  demographic_constraints:
    ecog_max: 2

recommended_regimen: REG-ADT-ENZALUTAMIDE
concurrent_therapy: []
followed_by: []

evidence_level: high
strength_of_recommendation: strong
nccn_category: "1"

expected_outcomes:
  overall_response_rate: "PSA decline ≥50% in ~78%"
  median_radiographic_pfs_months: 20
  median_overall_survival_months: 35

hard_contraindications: []
red_flags_triggering_alternative:
  - RF-PROSTATE-HIGH-RISK-BIOLOGY
required_tests:
  - TEST-PSA-SERUM
  - TEST-TESTOSTERONE-SERUM
  - TEST-BONE-SCAN
  - TEST-GERMLINE-BRCA-PANEL
desired_tests:
  - TEST-PSMA-PET
  - TEST-SOMATIC-HRR-PANEL

sources:
  - source_id: SRC-NCCN-PROSTATE-2025
    weight: primary
  - source_id: SRC-ESMO-PROSTATE-2024
    weight: primary

last_reviewed: null
reviewers: []

notes: >
  Workhorse mCRPC 1L for non-HRR-mutant disease with prior ADT exposure.
  Patients ARPI-naive (rare in modern era — most have had ARPI in mHSPC):
  enzalutamide / abiraterone preferred. Patients with prior ARPI: switch
  ARPI not generally recommended; consider docetaxel, PARPi (if HRR+),
  or Lu-PSMA (if PSMA-PET+).
"""),
    ("ind_prostate_mcrpc_1l_parpi.yaml", """\
id: IND-PROSTATE-MCRPC-1L-PARPI
plan_track: aggressive

applicable_to:
  disease_id: DIS-PROSTATE
  disease_state: mCRPC
  line_of_therapy: 1
  stage_requirements: ["IV"]
  biomarker_requirements_required:
    - biomarker_id: BIO-HRR-PANEL
      value_constraint: "positive"
      required: true
  biomarker_requirements_excluded: []
  demographic_constraints:
    ecog_max: 2

recommended_regimen: REG-OLAPARIB-MONO
concurrent_therapy: []
followed_by: []

evidence_level: high
strength_of_recommendation: strong
nccn_category: "1"

expected_outcomes:
  overall_response_rate: "Confirmed objective response ~33% in BRCA-mutant"
  median_radiographic_pfs_months: 7.4
  median_overall_survival_months: 19

hard_contraindications: []
red_flags_triggering_alternative: []
required_tests:
  - TEST-PSA-SERUM
  - TEST-TESTOSTERONE-SERUM
  - TEST-BONE-SCAN
  - TEST-GERMLINE-BRCA-PANEL
  - TEST-SOMATIC-HRR-PANEL
desired_tests:
  - TEST-PSMA-PET

sources:
  - source_id: SRC-NCCN-PROSTATE-2025
    weight: primary
  - source_id: SRC-ESMO-PROSTATE-2024
    weight: primary

last_reviewed: null
reviewers: []

notes: >
  PROfound: olaparib post-ARPI in HRR-mutant mCRPC. BRCA1/2 (Cohort A)
  largest benefit; broader HRR (Cohort B) smaller benefit. Talazoparib
  + enzalutamide (TALAPRO-2) and niraparib + abiraterone (MAGNITUDE)
  alternative HRR-mutant regimens. Reimbursement gap in Ukraine for
  prostate-specific PARPi indication.
"""),
    ("ind_prostate_mcrpc_2l_lu_psma.yaml", """\
id: IND-PROSTATE-MCRPC-2L-LU-PSMA
plan_track: standard

applicable_to:
  disease_id: DIS-PROSTATE
  disease_state: mCRPC
  line_of_therapy: 2
  stage_requirements: ["IV"]
  biomarker_requirements_required:
    - biomarker_id: BIO-PSMA-PET
      value_constraint: "positive"
      required: true
  biomarker_requirements_excluded: []
  demographic_constraints:
    ecog_max: 2

recommended_regimen: REG-LUTETIUM-PSMA
concurrent_therapy: []
followed_by: []

evidence_level: high
strength_of_recommendation: strong
nccn_category: "1"

expected_outcomes:
  overall_response_rate: "PSA decline ≥50% in ~46%"
  median_radiographic_pfs_months: 8.7
  median_overall_survival_months: 15.3

hard_contraindications: []
red_flags_triggering_alternative: []
required_tests:
  - TEST-PSMA-PET
  - TEST-PSA-SERUM
desired_tests: []

sources:
  - source_id: SRC-NCCN-PROSTATE-2025
    weight: primary
  - source_id: SRC-ESMO-PROSTATE-2024
    weight: primary

last_reviewed: null
reviewers: []

notes: >
  VISION: Lu-PSMA-617 in PSMA-positive mCRPC post-ARPI + post-taxane.
  Requires PSMA-PET-positive disease per VISION criteria. UA-access
  major barrier — 2-3 academic centers + international referral.
"""),
]


# ── 10. Algorithms (2) ───────────────────────────────────────────────


ALGORITHMS: list[tuple[str, str]] = [
    ("algo_prostate_mhspc_1l.yaml", """\
id: ALGO-PROSTATE-MHSPC-1L
applicable_to_disease: DIS-PROSTATE
applicable_to_disease_state: mHSPC
applicable_to_line_of_therapy: 1
purpose: >
  Select 1L mHSPC regimen. Default: ADT + ARPI (abiraterone preferred per
  LATITUDE; enzalutamide/apalutamide acceptable). High-volume CHAARTED
  criteria + docetaxel-eligible: ARASENS triplet. Frail elderly:
  de-escalate to ADT + ARPI mono.

output_indications:
  - IND-PROSTATE-MHSPC-1L-ARPI-DOUBLET
  - IND-PROSTATE-MHSPC-1L-TRIPLET

default_indication: IND-PROSTATE-MHSPC-1L-ARPI-DOUBLET
alternative_indication: IND-PROSTATE-MHSPC-1L-TRIPLET

decision_tree:
  # Step 1 — frailty / elderly: never triplet
  - step: 1
    evaluate:
      any_of:
        - red_flag: RF-PROSTATE-FRAILTY-AGE
    if_true:
      result: IND-PROSTATE-MHSPC-1L-ARPI-DOUBLET
    if_false:
      next_step: 2
  # Step 2 — high-volume disease (CHAARTED) + fit → triplet
  - step: 2
    evaluate:
      all_of:
        - condition: "High-volume disease per CHAARTED (visceral mets OR ≥4 bone lesions with ≥1 beyond axial skeleton)"
        - condition: "Docetaxel-eligible (ECOG 0-1, no significant comorbidity)"
    if_true:
      result: IND-PROSTATE-MHSPC-1L-TRIPLET
    if_false:
      result: IND-PROSTATE-MHSPC-1L-ARPI-DOUBLET

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  Decision_tree captures the two main 1L decision points: frailty
  (de-escalate) and volume (intensify). Engine routes through these
  before defaulting to ADT + ARPI doublet.
"""),
    ("algo_prostate_mcrpc_1l.yaml", """\
id: ALGO-PROSTATE-MCRPC-1L
applicable_to_disease: DIS-PROSTATE
applicable_to_disease_state: mCRPC
applicable_to_line_of_therapy: 1
purpose: >
  Select 1L mCRPC regimen for patient progressing on ADT (post-mHSPC ARPI
  exposure assumed). HRR-mutant: PARPi-first (PROfound). Non-HRR-mutant:
  switch ARPI or docetaxel based on prior exposure and visceral burden.
  PSMA-PET-positive post-2-prior-line: Lu-PSMA candidacy.

output_indications:
  - IND-PROSTATE-MCRPC-1L-ARPI
  - IND-PROSTATE-MCRPC-1L-PARPI

default_indication: IND-PROSTATE-MCRPC-1L-ARPI
alternative_indication: IND-PROSTATE-MCRPC-1L-PARPI

decision_tree:
  # Step 1 — HRR-mutant → PARPi (BRCA1/2 largest benefit)
  - step: 1
    evaluate:
      any_of:
        - red_flag: RF-PROSTATE-HIGH-RISK-BIOLOGY
    if_true:
      result: IND-PROSTATE-MCRPC-1L-PARPI
    if_false:
      result: IND-PROSTATE-MCRPC-1L-ARPI

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  PARPi prioritized when HRR-mutant — best evidence (PROfound). Non-HRR
  mCRPC defaults to ARPI switch (limited data; consider docetaxel if
  visceral mets or rapid progression). PSMA-Lu typically 2L+ after
  failure of taxane + ARPI.
"""),
]


# ── 11. SupportiveCare (1 prostate-specific) ──────────────────────────


SUPPORTIVE: dict[str, str] = {
    "sup_bone_health_prostate.yaml": """\
id: SUP-BONE-HEALTH-PROSTATE
intervention_type: bone_protection
name: "Prostate-cancer bone-health prophylaxis"
name_ua: "Профілактика кісткового здоров'я при РПЗ"

rationale: >
  Prevent skeletal-related events (fractures, spinal cord compression,
  bone-pain crises) and ADT-induced osteoporosis. Required for all
  patients on long-term ADT and especially for bone-metastatic disease.

standard_intervention:
  drug_id: DRUG-DENOSUMAB
  dose: "120 mg SC q4 weeks (bone-metastatic; Xgeva indication)"
  alternative_dose: "60 mg SC q6 months (ADT-induced osteoporosis without bone mets; Prolia indication)"

alternatives:
  - drug_id: DRUG-ZOLEDRONATE
    dose: "4 mg IV q4 weeks (bone-metastatic)"
    notes: "Renal dose adjustment required; avoid CrCl <30. Cheaper than denosumab + reimbursed."

co_interventions:
  - "Calcium 500-1000 mg PO daily"
  - "Vitamin D 400-800 IU PO daily (or higher if deficient)"
  - "Pre-treatment dental evaluation (ONJ risk mitigation)"
  - "Avoid invasive dental procedures during treatment"
  - "Baseline + serial DEXA scan (if no overt bone mets)"

contraindications:
  - "Severe renal impairment for zoledronate (CrCl <30)"
  - "Active dental infection / ONJ history (defer or switch agent)"
  - "Hypocalcemia (correct before initiation)"

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  Denosumab vs zoledronate: denosumab slightly superior SRE delay; no
  renal-adjustment needed; rebound vertebral fractures if abruptly
  stopped — taper carefully. Zoledronate cheaper and reimbursed in
  Ukraine; equivalent for most clinical purposes.
""",
    "sup_g_csf_primary_prophylaxis_prostate.yaml": """\
id: SUP-G-CSF-PRIMARY-PROPHYLAXIS-PROSTATE
intervention_type: growth_factor
name: "Primary G-CSF prophylaxis for ARASENS triplet (prostate)"
name_ua: "Первинна профілактика Г-КСФ для трипл ARASENS (РПЗ)"

rationale: >
  Prevent febrile neutropenia during docetaxel-containing ARASENS triplet
  in mHSPC (FN risk ≥10-20% with patient risk factors per ESMO/ASCO).
  Standard of care from cycle 1 in elderly / fragile / prior-chemo
  patients receiving the triplet.

standard_intervention:
  drug_id: DRUG-FILGRASTIM
  dose: "5 mcg/kg SC daily x 7-10 days starting ~24 hours post-chemo"

alternatives: []

co_interventions:
  - "Patient education on neutropenic-fever symptoms (fever ≥38.3°C OR ≥38.0°C sustained)"
  - "24/7 access pathway to chemo-experienced medical team"

contraindications: []

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  Disease-scoped entry to avoid colliding with potential cross-disease
  consolidation later. Filgrastim biosimilars НСЗУ-reimbursed in UA;
  pegfilgrastim alternative not yet in KB.
""",
}


# ── 12. Contraindications (2) ────────────────────────────────────────


CONTRAS: dict[str, str] = {
    "ci_prostate_seizure_history_enzalutamide.yaml": """\
id: CI-PROSTATE-SEIZURE-HISTORY-ENZALUTAMIDE
description: "History of seizures or condition predisposing to seizures (e.g., brain metastases, recent stroke) — enzalutamide contraindicated due to dose-dependent seizure risk (~0.4% in pivotal trials)."
description_ua: "Анамнез судом або стани, що схиляють до них (наприклад, метастази в мозок, нещодавній інсульт) — ензалутамід протипоказаний через дозозалежний ризик судом (~0.4% у реєстраційних дослідженнях)."

severity: absolute

trigger:
  type: composite_clinical
  any_of:
    - finding: "seizure_history"
      value: true
    - finding: "brain_metastases"
      value: true

affects_drugs:
  - DRUG-ENZALUTAMIDE
affects_regimens:
  - REG-ADT-ENZALUTAMIDE
affects_indications: []

sources: [SRC-NCCN-PROSTATE-2025, SRC-ESMO-PROSTATE-2024]
last_reviewed: null
notes: >
  Apalutamide and darolutamide do NOT carry the same seizure warning
  (lower CNS penetration). Patients with seizure history can safely
  receive these alternatives.
""",
    "ci_prostate_lutetium_visceral_only.yaml": """\
id: CI-PROSTATE-LUTETIUM-VISCERAL-ONLY
description: "PSMA-PET-negative or insufficient PSMA-positive uptake (per VISION criteria) — Lu-PSMA contraindicated as inadequate target expression."
description_ua: "ПСМА-ПЕТ-негативне або недостатнє ПСМА-позитивне поглинання (за критеріями VISION) — лютецій-ПСМА протипоказаний через недостатню експресію мішені."

severity: absolute

trigger:
  type: imaging_finding
  any_of:
    - finding: "psma_pet_negative"
      value: true
    - finding: "psma_uptake_insufficient_per_vision"
      value: true

affects_drugs:
  - DRUG-LUTETIUM-177-PSMA
affects_regimens:
  - REG-LUTETIUM-PSMA
affects_indications:
  - IND-PROSTATE-MCRPC-2L-LU-PSMA

sources: [SRC-NCCN-PROSTATE-2025]
last_reviewed: null
notes: >
  ~10-15% of mCRPC patients are PSMA-PET-negative or have heterogeneous
  uptake disqualifying for Lu-PSMA per VISION criteria. Required
  pre-screening test with significant sensitivity / specificity caveats.
""",
}


# ── DRIVER ─────────────────────────────────────────────────────────────


def main() -> int:
    write("diseases/prostate_cancer.yaml", DISEASE)
    for fname, body in SOURCES.items():
        write(f"sources/{fname}", body)
    for fname, body in DRUGS:
        write(f"drugs/{fname}", body)
    for fname, body in BIOMARKERS:
        write(f"biomarkers/{fname}", body)
    for fname, body in TESTS:
        write(f"tests/{fname}", body)
    write("workups/workup_metastatic_prostate.yaml", WORKUP)
    for fname, body in REGIMENS:
        write(f"regimens/{fname}", body)
    for fname, body in REDFLAGS:
        write(f"redflags/{fname}", body)
    for fname, body in INDICATIONS:
        write(f"indications/{fname}", body)
    for fname, body in ALGORITHMS:
        write(f"algorithms/{fname}", body)
    for fname, body in SUPPORTIVE.items():
        write(f"supportive_care/{fname}", body)
    for fname, body in CONTRAS.items():
        write(f"contraindications/{fname}", body)
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
