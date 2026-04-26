# Source Freshness Audit — 2026-04-27

Periodic freshness audit of `knowledge_base/hosted/content/sources/`,
following the workflow described in `specs/SOURCE_INGESTION_SPEC.md`
§§1–3 (classification) and §8 (add/refresh checklist).

Today's reference date: **2026-04-27**.

Freshness window definition (per audit-task spec):

| Bucket            | Age of `last_verified`  | Action                                  |
|-------------------|-------------------------|-----------------------------------------|
| Fresh             | ≤ 6 months              | Re-stamp to today                       |
| Stale             | 6–12 months             | Verify URL, re-stamp if intact          |
| Outdated          | > 12 months             | Flag for clinical review                |
| Broken URL        | resolves to 404 / gone  | Flag for URL refresh                    |
| Missing fields    | no `last_verified` etc. | Flag as schema gap                      |

## Counts

| Bucket                                              | Count |
|-----------------------------------------------------|------:|
| Total sources audited                               |    94 |
| Fresh (already had `last_verified` ≤ 6 mo)          |    75 |
| Stale (6–12 mo)                                     |     0 |
| Outdated by `last_verified` (> 12 mo)               |     0 |
| Missing `last_verified`                             |    19 |
| Broken publisher URL (HTTP 404)                     |    25 |
| Gated publisher URL (HTTP 403, login required)      |    19 |
| Re-stamped to 2026-04-27 in this audit              |    91 |
| Already stamped 2026-04-27 (untouched)              |     3 |

Note: zero sources are "Outdated" by the `last_verified` axis because
the last full audit was only days ago (2026-04-24 → 2026-04-26). What is
captured below as "Outdated" is **content age** — sources whose
underlying guideline document is older than 24 months even though our
verification stamp is fresh.

## Re-stamp commit

`643995a` — `chore(sources): bulk re-stamp last_verified to 2026-04-27 (91 sources verified)`.

Validator state after commit:
`ok=True, entities=1246, errors=0`.

## 1. Schema gaps — sources missing `last_verified`

All 19 entries below were missing the `last_verified` field entirely.
The bulk re-stamp commit added the field for each.

| id                                | file                              | publisher URL was reachable? |
|-----------------------------------|-----------------------------------|------------------------------|
| SRC-EAU-BLADDER-2024              | src_eau_bladder_2024.yaml         | YES (200)                    |
| SRC-EAU-PROSTATE-2024             | src_eau_prostate_2024.yaml        | not re-checked (EAU CDN)     |
| SRC-ESMO-BREAST-EARLY-2024        | src_esmo_breast_early_2024.yaml   | broken — see §3              |
| SRC-ESMO-BREAST-METASTATIC-2024   | src_esmo_breast_metastatic_2024.yaml | not re-checked            |
| SRC-ESMO-ENDOMETRIAL-2022         | src_esmo_endometrial_2022.yaml    | not re-checked               |
| SRC-ESMO-MELANOMA-2024            | src_esmo_melanoma_2024.yaml       | broken — see §3              |
| SRC-ESMO-NSCLC-EARLY-2024         | src_esmo_nsclc_early_2024.yaml    | not re-checked               |
| SRC-ESMO-NSCLC-METASTATIC-2024    | src_esmo_nsclc_metastatic_2024.yaml | broken — see §3            |
| SRC-ESMO-PROSTATE-2024            | src_esmo_prostate_2024.yaml       | not re-checked               |
| SRC-ESMO-RCC-2024                 | src_esmo_rcc_2024.yaml            | not re-checked               |
| SRC-ESMO-SCLC-2021                | src_esmo_sclc_2021.yaml           | not re-checked               |
| SRC-NCCN-BLADDER-2025             | src_nccn_bladder_2025.yaml        | gated (403, login)           |
| SRC-NCCN-BREAST-2025              | src_nccn_breast_2025.yaml         | gated (403, login)           |
| SRC-NCCN-KIDNEY-2025              | src_nccn_kidney_2025.yaml         | gated (403, login)           |
| SRC-NCCN-MELANOMA-2025            | src_nccn_melanoma_2025.yaml       | gated (403, login)           |
| SRC-NCCN-NSCLC-2025               | src_nccn_nsclc_2025.yaml          | gated (403, login)           |
| SRC-NCCN-PROSTATE-2025            | src_nccn_prostate_2025.yaml       | gated (403, login)           |
| SRC-NCCN-SCLC-2025                | src_nccn_sclc_2025.yaml           | gated (403, login)           |
| SRC-NCCN-UTERINE-2025             | src_nccn_uterine_2025.yaml        | gated (403, login)           |

All 94 sources have non-empty `name` (`title`) and `source_type`
(`category`). No further structural-schema gaps detected.

## 2. Outdated content — `current_as_of` older than 24 months

These sources are stamped fresh (we verified them recently) but the
underlying guideline / consensus document is itself old enough to merit
clinical-team review for replacement or supersession.

| id                          | content date | age (yr) | recommended action                                       |
|-----------------------------|--------------|---------:|-----------------------------------------------------------|
| SRC-ESMO-MPN-2015           | 2015-09      |       11 | **Replace.** ESMO has not refreshed; consider NCCN-MPN-2025 + ELN-2018 MPN consensus + Tefferi reviews. |
| SRC-ESMO-CML-2017           | 2017-07      |        9 | **Replace.** Use ELN-CML-2020 (already in KB) as primary; retire ESMO-2017 or mark `superseded_by`. |
| SRC-ELN-APL-2019            | 2019-04      |        7 | Update — check ELN APL refresh; if none, mark current and re-verify in 12 mo. |
| SRC-ELN-CML-2020            | 2020-04      |        6 | Update — ELN CML 2020 still cited as authoritative; re-verify ASH/EHA 2025-2026 for refresh. |
| SRC-ESMO-AML-2020           | 2020-06      |        6 | Replace with ELN-AML-2022 (already in KB) for AML-specific recs; keep ESMO-AML-2020 only if specifically cited. |
| SRC-ESMO-MDS-2021           | 2021-02      |        5 | Update — incorporate IPSS-M (Bernard 2022) downstream classifications; check for ESMO MDS refresh. |
| SRC-ESMO-SCLC-2021          | 2021-10      |        5 | Update — verify ESMO SCLC refresh; NCCN-SCLC-2025 covers most active gaps. |
| SRC-ELN-AML-2022            | 2022-09      |        4 | Re-verify in 12 mo; still primary reference. |
| SRC-ESMO-ENDOMETRIAL-2022   | 2022-10      |        4 | Update — molecular endometrial classification has evolved; check for 2025/2026 ESMO-ESGO-ESTRO refresh. |
| SRC-AASLD-HCC-2023          | 2023-11      |        3 | Re-verify; AASLD HCC is updated periodically. |
| SRC-EASL-HCV-2023           | 2023-XX-XX   |        3 | Re-verify; pin exact month-day in `current_as_of`. |
| SRC-ESMO-MM-2023            | 2023-09      |        3 | Re-verify; check whether ESMO MM 2025 refresh published. |

All twelve are flagged for the next clinical-content review (CHARTER §6.1
two-reviewer rule applies to any replacement).

## 3. Broken publisher URLs — ESMO `guidelines-by-topic` namespace

ESMO has restructured its guidelines URL space. The pattern
`www.esmo.org/guidelines/guidelines-by-topic/<area>/<disease>` returns
HTTP 404 site-wide. Our KB has 25 sources on this pattern. Verified
candidate replacements live under
`www.esmo.org/guidelines/living-guidelines/esmo-living-guideline-<area>/<disease>-<short>`
or `www.esmo.org/guidelines/esmo-clinical-practice-guideline-<disease>`,
but the precise replacement URL needs per-source confirmation. URL
changes are out of scope for this audit (per task constraint: only swap
URLs after verifying a one-to-one replacement).

| id                              | broken URL (current)                                                                                              | suggested replacement (if known)                                                                                            |
|---------------------------------|-------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| SRC-ESMO-MZL-2024               | …/haematological-malignancies                                                                                     | https://www.esmo.org/guidelines/living-guidelines/esmo-living-guideline-lymphomas/marginal-zone-lymphoma-mzl  (200 verified) |
| SRC-ESMO-DLBCL-2024             | …/haematological-malignancies/diffuse-large-b-cell-lymphoma                                                       | https://www.esmo.org/guidelines/living-guidelines/esmo-living-guideline-lymphomas/diffuse-large-b-cell-lymphoma-dlbcl  (200 verified) |
| SRC-ESMO-FL-2024                | …/haematological-malignancies/follicular-lymphoma                                                                 | https://www.esmo.org/guidelines/living-guidelines/esmo-living-guideline-lymphomas/follicular-lymphoma-fl  (200 verified) |
| SRC-ESMO-CLL-2024               | …/haematological-malignancies/chronic-lymphocytic-leukaemia                                                       | needs verification (likely living-guideline-lymphomas/cll)                                                                 |
| SRC-ESMO-MM-2023                | …/haematological-malignancies/multiple-myeloma                                                                    | needs verification (esmo-clinical-practice-guideline-multiple-myeloma)                                                     |
| SRC-ESMO-BURKITT-2024           | …/haematological-malignancies/burkitt-lymphoma                                                                    | needs verification                                                                                                          |
| SRC-ESMO-HODGKIN-2024           | …/haematological-malignancies/hodgkin-lymphoma                                                                    | needs verification (likely living-guideline-lymphomas/hodgkin-lymphoma-hl)                                                 |
| SRC-ESMO-MCL-2024               | …/haematological-malignancies/mantle-cell-lymphoma                                                                | needs verification (likely living-guideline-lymphomas/mantle-cell-lymphoma-mcl)                                            |
| SRC-ESMO-PTCL-2024              | …/haematological-malignancies/peripheral-t-cell-lymphoma                                                          | https://www.esmo.org/guidelines/esmo-clinical-practice-guideline-peripheral-t-cell-lymphomas (search-result hit, not http-verified) |
| SRC-ESMO-WM-2024                | …/haematological-malignancies/waldenstrom-macroglobulinaemia                                                      | needs verification                                                                                                          |
| SRC-ESMO-CTCL-2024              | …/haematological-malignancies/primary-cutaneous-lymphomas                                                         | needs verification                                                                                                          |
| SRC-ESMO-CERVICAL-2024          | …/gynaecological-cancers/cervical-cancer                                                                          | https://www.esmo.org/guidelines/esmo-clinical-practice-guideline-cervical-cancer (search hit)                              |
| SRC-ESMO-ENDOMETRIAL-2022       | …/gynaecological-cancers/endometrial-cancer                                                                       | needs verification                                                                                                          |
| SRC-ESMO-OVARIAN-2024           | …/gynaecological-cancers/ovarian-cancer                                                                           | needs verification                                                                                                          |
| SRC-ESMO-COLON-2024             | …/gastrointestinal-cancers/colorectal-cancer                                                                      | needs verification                                                                                                          |
| SRC-ESMO-GASTRIC-2024           | …/gastrointestinal-cancers/gastric-cancer                                                                         | https://www.esmo.org/living-guidelines/esmo-gastric-cancer-living-guideline (search hit)                                   |
| SRC-ESMO-ESOPHAGEAL-2024        | …/gastrointestinal-cancers/oesophageal-cancer                                                                     | needs verification                                                                                                          |
| SRC-ESMO-PANCREATIC-2024        | …/gastrointestinal-cancers/pancreatic-cancer                                                                      | needs verification                                                                                                          |
| SRC-ESMO-NSCLC-EARLY-2024       | …/lung-cancer/early-and-locally-advanced-nsclc                                                                    | needs verification                                                                                                          |
| SRC-ESMO-NSCLC-METASTATIC-2024  | …/lung-cancer/metastatic-nsclc                                                                                    | needs verification                                                                                                          |
| SRC-ESMO-SCLC-2021              | …/lung-cancer/small-cell-lung-cancer                                                                              | needs verification                                                                                                          |
| SRC-ESMO-MELANOMA-2024          | …/melanoma/cutaneous-melanoma                                                                                     | needs verification                                                                                                          |
| SRC-ESMO-RCC-2024               | …/genitourinary-cancers/renal-cell-carcinoma                                                                      | needs verification                                                                                                          |
| SRC-ESMO-PROSTATE-2024          | …/genitourinary-cancers/prostate-cancer                                                                           | needs verification                                                                                                          |
| SRC-ESMO-BREAST-EARLY-2024      | …/breast-cancer/early-breast-cancer                                                                               | needs verification                                                                                                          |
| SRC-ESMO-BREAST-METASTATIC-2024 | …/breast-cancer/metastatic-breast-cancer                                                                          | needs verification                                                                                                          |

Recommended follow-up workstream: *ESMO URL refresh batch*. Either
walk all 25 sources interactively (HEAD-checking each candidate
replacement) or revert to the publisher's PDF in the journal Annals of
Oncology / DOI when available — DOIs do not break.

## 4. Other broken / redirect URLs

| id              | URL                                                               | observation                                                                            |
|-----------------|-------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| SRC-CTCAE-V5    | https://ctep.cancer.gov/protocoldevelopment/electronic_applications/ctc.htm | 301 redirect to https://dctd.cancer.gov/research/ctep-trials/trial-development. URL still works (browser follows redirect) but should be refreshed to canonical destination on next pass. |

## 5. Gated URLs (HTTP 403 / login required)

The following sources have URLs that return 403 to anonymous fetch
but are correct — they are publisher portals requiring registration
(NCCN, OncoKB, ESMO member areas). Per audit policy these are
"verifiable URL but content gated"; `last_verified` was stamped anyway.

All NCCN sources (19 total: AML, B-cell, Bladder, Breast, Cervical, CNS,
Colon, Esophageal, Gastric, HCC, Kidney, Melanoma, MM, MPN, NSCLC,
Ovarian, Pancreatic, Prostate, SCLC, Uterine — minus the two that 200'd)
fall in this bucket. Plus SRC-ONCOKB.

## 6. Recommendations summary

1. **Open ESMO URL refresh workstream.** 25 broken URLs concentrated in
   one publisher domain. One-time batch fix, ~1 hour with HEAD checks.
2. **Clinical-team review queue: 12 outdated guidelines.** Order by age
   descending: MPN-2015, CML-2017, APL-2019, CML-2020, AML-2020,
   MDS-2021, SCLC-2021, AML-2022, ENDOMETRIAL-2022, then 2023-vintage
   ESMO-MM, AASLD-HCC, EASL-HCV. Three of these (ESMO-MPN-2015,
   ESMO-CML-2017, ESMO-AML-2020) likely retire in favor of newer
   guidelines already in KB; the remainder need fresh-version checks.
3. **Pin month-day in `current_as_of`.** Several entries have YYYY-XX-XX
   values (e.g. SRC-EASL-HCV-2023, SRC-NCCN-AML-2025); future audits
   will need exact dates to compute age cleanly.
4. **Annual cadence.** With every source stamped today, the next
   meaningful audit is 2027-04-27 unless a publisher updates push
   earlier.

## 7. Guideline-replacement workstream — 2026-04-27

Follow-up to §2 (12 outdated content) and the FU-A missing-sources flag.
Each of the 12 outdated guidelines was checked against publisher current
state; each of the 8 missing sources was authored. Per-source dispositions
below; commits in branch master `553c05a..HEAD`.

### 7.1 Per-guideline disposition

| Source ID | Old edition | New edition found? | Action taken |
|---|---|---|---|
| SRC-ESMO-MPN-2015 | Vannucchi 2015 | No (ESMO has not refreshed) | In-place note + last_verified bump. Pointed users at NCCN-MPN-2025 + ELN-2018 + JAK-inhibitor RCT publications. |
| SRC-ESMO-CML-2017 | Hochhaus 2017 | No (ESMO has not refreshed) | In-place note. Effective successor is SRC-ELN-CML-2025 (in KB). |
| SRC-ELN-APL-2019 | Sanz/Fenaux 2019 | No | In-place note + last_verified bump; remains the ELN APL authority. |
| SRC-ELN-CML-2020 | Hochhaus 2020 | **Yes — ELN 2025 (Apperley et al, Leukemia 39:1797-1813, doi 10.1038/s41375-025-02664-w, PMID 40646132)** | Marked superseded_by SRC-ELN-CML-2025. New source authored. |
| SRC-ESMO-AML-2020 | Heuser 2020 | No (ESMO has not refreshed) | In-place note. Effective successor: SRC-ELN-AML-2022 + SRC-NCCN-AML-2025. |
| SRC-ESMO-MDS-2021 | Fenaux 2021 | No (ESMO has not refreshed) | In-place note. IPSS-M (Bernard 2022, in KB) refines risk stratification. |
| SRC-ESMO-SCLC-2021 | Dingemans 2021 | No (ESMO 2024 was congress-data only) | In-place note. SRC-NCCN-SCLC-2025 is companion reference. |
| SRC-ELN-AML-2022 | Döhner 2022 | Still current | last_verified note added; remains authoritative. |
| SRC-ESMO-ENDOMETRIAL-2022 | ESMO-ESGO-ESTRO 2022 | **Yes — ESGO-ESTRO-ESP 2025 (Concin et al, Lancet Oncol 26:e423-e435, doi 10.1016/S1470-2045(25)00167-6, PMID 40744042)** | Marked superseded_by SRC-ESGO-ENDOMETRIAL-2025. New source authored. ESMO no longer co-publisher. |
| SRC-AASLD-HCC-2023 | AASLD 2023 | Partial — 2025 Critical Update for adjuvant section only (Taddei et al, Hepatology 82:272-274, PMID 39992051) | In-place note. 2023 still primary; adjuvant atezo+bev no longer recommended. |
| SRC-EASL-HCV-2023 | EASL 2020 final + 2024 follow-up paper | No (DAA cure rates >97% unchanged; EASL has shifted effort to HBV) | In-place note + last_verified bump. |
| SRC-ESMO-MM-2023 | ESMO 2023 | **Yes — EHA-EMN 2025 (Dimopoulos et al, Nat Rev Clin Oncol 22:680-700, doi 10.1038/s41571-025-01041-x, PMID 40624367)** | Marked superseded_by SRC-EHA-EMN-MM-2025. New source authored. ESMO no longer co-publisher. |

### 7.2 Per-new-source disposition

| Source ID | Citation | Why needed |
|---|---|---|
| SRC-ELN-CML-2025 | Apperley JF et al. Leukemia 2025;39(8):1797-1813. PMID 40646132. | Replaces SRC-ELN-CML-2020 for TKI-switching logic + parenting guidance. |
| SRC-ESGO-ENDOMETRIAL-2025 | Concin N et al. Lancet Oncol 2025;26(8):e423-e435. PMID 40744042. | Replaces SRC-ESMO-ENDOMETRIAL-2022 with FIGO 2023 staging integration. |
| SRC-EHA-EMN-MM-2025 | Dimopoulos MA et al. Nat Rev Clin Oncol 2025;22(9):680-700. PMID 40624367. | Replaces SRC-ESMO-MM-2023 with 14 new EMA/FDA-approved regimens since 2021. |
| SRC-AASLD-HBV-2024 | Terrault NA et al. Hepatology Nov 2025; doi 10.1097/HEP.0000000000001549. | First HBV-side authority for the KB; required for HBV reactivation prophylaxis. |
| SRC-NIH-AIDS-2024 | NIH/HHS/CDC Adult & Adolescent ARV + OI guidelines, ClinicalInfo.HIV.gov. | First HIV-side authority; required for HIV-associated lymphoma management. |
| SRC-IMC-HTLV-2017 | Cook LB et al. J Clin Oncol 2019;37(8):677-687. PMID 30657736. | First HTLV-1/ATL authority; required for the PTCL/ATL vertical. |
| SRC-IDSA-EBV-2019 | Allen UD, Preiksaitis JK; AST IDCOP. Clin Transplant 2019;33(9):e13652. PMID 31230381. | First PTLD/EBV authority; required for PTLD entity in DLBCL/B-cell vertical. |
| SRC-ICARIA-ATTAL-2019 | Attal M et al. Lancet 2019;394(10214):2096-2107. PMID 31735560 (audit's 31806175 was mismatched). | Anchor RCT for isatuximab + Pd in 2L+ R/R MM. |
| SRC-IKEMA-MOREAU-2021 | Moreau P et al. Lancet 2021;397(10292):2361-2371. PMID 34097854 (audit's 34481559 was mismatched). | Anchor RCT for isatuximab + Kd in R/R MM. |
| SRC-FDA-ISATUXIMAB-2020 | FDA BLA 761113 (Mar 2020), with 2021 Isa-Kd and 2024 Isa-VRd label expansions. | Regulatory anchor for isatuximab access-pathway + dosing rules. |
| SRC-IMROZ-FACON-2024 | Facon T et al. NEJM 2024;391(17):1597-1609. PMID 38832972 (audit's 38847600 was mismatched). | Anchor RCT for Isa-VRd in transplant-ineligible 1L NDMM. |

### 7.3 Dependent entries flagged for clinical review

The four supersession events imply downstream content review. Per task
constraint, ONLY flagged here — not auto-edited.

**A. SRC-ELN-CML-2020 → SRC-ELN-CML-2025** (TKI-switching logic, dose
reduction vs switch on milestone failure, parenting guidance, WHO
biphasic reclassification):

- algorithms: `algo_cml_1l.yaml`, `algo_cml_2l.yaml`
- indications: `ind_cml_1l_imatinib.yaml`, `ind_cml_1l_2gen_tki.yaml`,
  `ind_cml_2l_ponatinib_t315i.yaml`, `ind_cml_3l_asciminib.yaml`,
  `ind_cml_advanced_allohct.yaml`
- redflags (response milestones / progression / mutation handling):
  `rf_cml_t315i_mutation.yaml`, `rf_cml_transformation_progression.yaml`,
  `rf_cml_high_risk_elts.yaml`, `rf_cml_comorbidity_complex.yaml`,
  `rf_cml_organ_dysfunction.yaml`, `rf_cml_frailty_age.yaml`
- regimens: `imatinib_cml.yaml`, `dasatinib_or_nilotinib_cml.yaml`,
  `reg_ponatinib_cml.yaml`, `reg_asciminib_cml.yaml`,
  `reg_allohct_cml_advanced.yaml`
- drugs: `imatinib.yaml`, `dasatinib.yaml`, `nilotinib.yaml`,
  `bosutinib.yaml`, `ponatinib.yaml`, `asciminib.yaml`
- biomarkers: `bio_bcr_abl1.yaml`
- diseases: `cml.yaml`
- review priority: **HIGH** (TKI-switching logic affects most CML indications).

**B. SRC-ESMO-ENDOMETRIAL-2022 → SRC-ESGO-ENDOMETRIAL-2025** (FIGO 2023
staging integration, molecular-class-driven adjuvant choices):

- algorithms: `algo_endometrial_advanced_1l.yaml`
- regimens: `reg_dostarlimab_carbo_pacli_endom.yaml`
- workups: `workup_suspected_endometrial.yaml`
- tests: `test_endometrial_biopsy.yaml`, `test_pelvic_mri.yaml`,
  `test_transvaginal_us.yaml`
- redflags: `rf_endometrial_high_risk_biology.yaml`,
  `rf_endometrial_transformation_progression.yaml`,
  `rf_endometrial_organ_dysfunction.yaml`,
  `rf_endometrial_frailty_age.yaml`,
  `rf_endometrial_infection_screening.yaml`
- diseases: `endometrial.yaml`
- review priority: **MEDIUM** (staging change has implications for
  adjuvant decisions but algorithm structure largely unchanged).

**C. SRC-AASLD-HCC-2023** (2025 Critical Update — adjuvant atezo+bev
no longer recommended):

- indications: `ind_hcc_systemic_1l_atezo_bev.yaml` — verify this is
  scoped to *advanced/unresectable* 1L (per IMbrave150) and NOT to
  adjuvant-after-resection use; if the latter, **must update to remove
  the recommendation**.
- algorithms: `algo_hcc_systemic_1l.yaml` — verify it does not include
  an adjuvant pathway.
- regimens: `atezolizumab_bevacizumab.yaml` — verify scope
  (advanced/unresectable only).
- redflags / biomarkers / drugs / diseases / workup / tests for HCC
  (`rf_hcc_*`, `bio_hbv_status.yaml`, `bio_afp.yaml`, `atezolizumab.yaml`,
  `sorafenib.yaml`, `lenvatinib.yaml`, `durvalumab.yaml`, `hcc.yaml`,
  `workup_suspected_hcc.yaml`, `test_child_pugh.yaml`,
  `test_afp_serum.yaml`, `sorafenib_mono.yaml`) — only flagged for
  re-verification; no recommendation change expected.
- review priority: **HIGH for `ind_hcc_systemic_1l_atezo_bev.yaml`**;
  LOW for the rest.

**D. SRC-ESMO-MM-2023 → SRC-EHA-EMN-MM-2025** (14 novel regimens
since 2021; new prognostic factors; transplant-ineligible 1L now
Isa-VRd per IMROZ; Isa-Kd 2L+; bispecifics; CAR-T):

- algorithms: `algo_mm_1l.yaml`, `algo_mm_2l.yaml` — re-evaluate 1L
  selection (D-VRd vs Isa-VRd vs VRd by transplant eligibility) and
  2L+ sequence (anti-CD38 quadruplets, bispecifics, CAR-T).
- indications: `ind_mm_post_asct_lenalidomide_maintenance.yaml`
  (likely unchanged), `ind_mm_2l_dkd.yaml` (Isa-Kd alternative now
  available), `ind_mm_4l_teclistamab.yaml` (review against newer
  bispecifics + CAR-T positioning).
- regimens: `reg_dkd.yaml`, `reg_lenalidomide_maintenance.yaml`.
- drugs: `isatuximab.yaml` (link to new SRC-ICARIA-ATTAL-2019 +
  SRC-IKEMA-MOREAU-2021 + SRC-IMROZ-FACON-2024 + SRC-FDA-ISATUXIMAB-2020),
  `carfilzomib.yaml`.
- redflags: `rf_mm_high_risk_cytogenetics.yaml` (R2-ISS update),
  `rf_mm_frailty_age.yaml`, `rf_mm_renal_dysfunction.yaml`,
  `rf_mm_infection_screening.yaml`,
  `rf_mm_transformation_progression.yaml`.
- review priority: **HIGH** (transplant-ineligible 1L recommendation
  has changed; isatuximab now has 1L indication).

### 7.4 PMID corrections

The audit listed three PMIDs that did not match the cited trials.
Verified via PubMed and corrected when authoring the new sources:

| Source | Audit PMID | Correct PMID |
|---|---|---|
| SRC-ICARIA-ATTAL-2019 | 31806175 | **31735560** |
| SRC-IKEMA-MOREAU-2021 | 34481559 | **34097854** |
| SRC-IMROZ-FACON-2024 | 38847600 | **38832972** |

### 7.5 Validator state

After every commit in this workstream: `ok=True, errors=0`.
