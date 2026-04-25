# OpenOnco

> **Open-source clinical decision support for oncology tumor boards.**
> Upload a patient profile → get two alternative treatment plans
> (standard + aggressive), side by side, with every recommendation cited.
> Plans refresh as new data arrives. All clinical logic lives in a
> declarative rule engine over a curated knowledge base — **no LLM
> picks regimens** (CHARTER §8.3).

🌐 **Live demo:** **[openonco.info](https://openonco.info)** — try it in the browser, no install needed.
📖 **Specifications-first:** every clinical statement traceable to a Source entity; dual clinical-lead review per [CHARTER §6.1](specs/CHARTER.md).
🏥 **FDA non-device CDS positioning** per [CHARTER §15](specs/CHARTER.md) — informational support tool, not a medical device.
📜 **License:** Code MIT · Content / specs CC BY 4.0.

---

## Why this exists

Picking a regimen for a real patient is **2–4 hours of manual desk work** for an oncologist or clinical pharmacologist: open NCCN PDF, cross-check ESMO, re-read the local protocol (МОЗ in Ukraine), verify formulary reimbursement, look up dose adjustments for renal/hepatic impairment, layer supportive care, remember vaccinations and OI prophylaxis. Every patient. Every time. One missed contraindication can be fatal.

OpenOnco automates the chore work. The clinician receives a **drafted plan with every citation already attached** and only needs to verify and tailor it for the specific patient. The logic mirrors a **classical multidisciplinary tumor board (MDT)**, augmented by an analytical layer — each "virtual specialist" is a versioned rule module with its own sources and `last_reviewed` stamp.

---

## Status

**v0.1.0-alpha — first public alpha.** All knowledge-base infrastructure is functional: schemas, rule engine, MDT orchestrator, render layer, plan revisions/supersedes loop, in-browser Pyodide demo, persistent reviewer-event log.

Currently covered: **lymphoid neoplasms (Tier 1 + Tier 2)** and **multiple myeloma 1L** end-to-end. Myeloid neoplasms (AML, APL, CML, MDS, MPN) are **actively being scaffolded** — track progress on the [Capabilities](https://openonco.info/capabilities.html) page (live counts).

All clinical content currently carries the **STUB** badge in rendered Plans — it stays STUB until two of three Clinical Co-Leads sign it off per CHARTER §6.1. This is by design; the badge is meant to be visible.

→ **Live KB metrics, per-disease coverage, and reviewer sign-off ratio:** [openonco.info/capabilities](https://openonco.info/capabilities.html)

---

## What it does

**Two-track plan generator (CHARTER §2).** For any covered disease, the engine produces at least two alternative treatment tracks **side by side** — never a single "system-prescribes-X" output. The HCP picks; the engine surfaces transparent rationale, red-flag triggers, hard contraindications, supportive care, monitoring schedule, expected outcomes with sourced numbers, and a "what NOT to do" list per indication.

**Versioned skill registry (16 specialists).** Hematologist, hematopathologist, infectious-disease/hepatology, radiologist, molecular geneticist, clinical pharmacist, radiation oncologist, surgical oncologist, transplant specialist, cellular-therapy (CAR-T) specialist, psychologist, palliative care, social worker / case manager, primary care, medical oncologist, generic pathologist. Each skill is a versioned rule bundle with `last_reviewed`, `clinical_lead`, `verified_by` sign-offs, and source citations.

**Diagnostic-phase MDT (CHARTER §15.2 C7).** When histology is not yet confirmed, the engine emits a **Workup Brief** (which tests to run, biopsy approach, IHC panel, mandatory questions) — never a treatment Plan. This is a mechanical hard gate against premature treatment recommendations.

**Plan revisions / supersedes loop.** New patient data → new Plan version via `revise_plan(...)`, polymorphic across `diagnostic→diagnostic`, `diagnostic→treatment` (promotion), and `treatment→treatment`. Refuses illegal `treatment→diagnostic` downgrade. Immutable supersedes / superseded_by audit chain (CHARTER §10.2).

**Append-only reviewer event log.** Clinicians can record `confirmed` / `modified` / `approved` / `rejected` events against any plan section via CLI (`python -m knowledge_base.engine.event_cli add ...`). Events persist as JSONL and rehydrate into the next Plan render — full audit trail per CHARTER §10.2 / §15.1 Criterion 4.

**Cross-disease biomarker entities.** Every clinically significant marker — TP53, IGHV, MYC, BCL2/BCL6 rearrangements, double-hit, MYD88 L265P, CXCR4-WHIM, BRAF V600E, EZH2 Y641, ALK, RHOA G17V, NOTCH1, CD20/CD30/CD52/CD79b, PD-L1, Ki-67, EBV, etc. — is a **single citable entity** with cross-disease decision impact documented. Composites (CLL high-risk genetics, MM cytogenetics-HR, double-hit) reference standalone components via `related_biomarkers`.

**FDA Criterion 4 metadata on every Plan.** `intended_use`, `hcp_user_specification`, `patient_population_match`, `algorithm_summary`, `data_sources_summary`, `data_limitations`, `automation_bias_warning`, `time_critical` flag. Full algorithm decision trace in every output.

**HTML render layer.** Single-file A4-printable HTML per Plan / Diagnostic Brief / Revision Note. Embedded CSS, no external assets beyond Google Fonts. Sections include etiological driver (for `etiologically_driven` archetype), pre-treatment investigations table, RedFlag PRO/CONTRA categorization, "what NOT to do", monitoring phases, timeline, MDT skill catalog with version + sign-off status. UA and EN render via `target_lang`.

**Live in-browser demo (Pyodide).** The actual Python engine runs **in the browser** at [openonco.info/try.html](https://openonco.info/try.html) — no backend, no patient data leaves the device.

**Translation infrastructure.** DeepL Free + LibreTranslate self-hosted fallback + on-disk cache + glossary protection (entity IDs, doses, codes never sent to a translator). Per CHARTER §8.3, every translation is flagged `machine_translated: true` for clinical review.

---

## Try it now

The fastest path is the **browser demo** — no install, no backend:

→ **[openonco.info/try.html](https://openonco.info/try.html)** — paste a patient JSON, click **Generate**, see the rendered Plan inline. The Pyodide-loaded engine is the same one that runs server-side.

Sample patients are available in the [examples gallery](https://openonco.info/gallery.html) — 30+ pre-rendered cases across DLBCL, FL, CLL/SLL, MCL, HCV-MZL, HCL, WM, HGBL-DH, PTCL, ALCL, AITL, MF/Sézary, cHL, NLPBL, and MM. Click any card → see the full Plan as the engine produced it.

### Run locally

```bash
git clone https://github.com/romeo111/OpenOnco.git
cd OpenOnco
pip install -e .

# Run the engine on a synthetic patient
python -m knowledge_base.engine.cli examples/patient_zero_indolent.json --mdt --render plan.html
# → open plan.html in a browser

# Record a clinician event against a plan
python -m knowledge_base.engine.event_cli add patient-001 \
    --event-type confirmed --target-type regimen --target-id REG-VRD \
    --summary "Confirmed VRd at MDT 2026-04-25" \
    --evidence NCCN-MM-2024 ESMO-MM-2023

# Run the test suite
pytest tests/

# Build the static site locally
python scripts/build_site.py --clean
python -m http.server 8000 --directory docs/   # → http://localhost:8000

# Inspect KB stats (entity counts, per-disease coverage, sign-off ratio)
python -m knowledge_base.stats
```

Python 3.11+ required.

---

## Repository layout

```
openonco/
├── specs/                          # 12+ specifications (UA primary)
├── knowledge_base/
│   ├── schemas/                    # Pydantic schemas
│   ├── engine/                     # rule engine, MDT, render, revisions, events
│   ├── validation/                 # YAML loader + ref-integrity checker
│   ├── clients/                    # source-API + translate clients
│   ├── stats.py                    # KB info dashboard (CLI + JSON + HTML widget)
│   └── hosted/content/             # YAML knowledge base (diseases, regimens, …)
├── examples/                       # synthetic patient profiles
├── scripts/build_site.py           # static-site builder (GitHub Pages)
├── docs/                           # generated site → openonco.info
├── tests/                          # full pytest suite
└── legacy/                         # retired autoresearch pipeline (archival only)
```

---

## How to contribute

OpenOnco is a public infrastructure project. **Every contribution helps a real oncologist save time and avoid mistakes.** A few ways to plug in:

### Try it and tell us what's wrong

The single most valuable contribution right now is **a clinician's eye on a rendered Plan**. Try the [demo](https://openonco.info/try.html) on a case you know well, find what's stale / missing / overconfident, and **open an issue** — even a one-line "this regimen is missing the dose adjustment for CrCl <30" is worth more than a long-form review.

→ **[Open a clinical-feedback issue](https://github.com/romeo111/OpenOnco/issues/new?labels=clinical-feedback)**

### Add a disease or fix a regimen

The knowledge base is YAML files under `knowledge_base/hosted/content/`. Authoring conventions:

- Read **[`specs/CLINICAL_CONTENT_STANDARDS.md`](specs/CLINICAL_CONTENT_STANDARDS.md)** — citation format, evidence levels, what counts as a Source.
- Read **[`specs/REDFLAG_AUTHORING_GUIDE.md`](specs/REDFLAG_AUTHORING_GUIDE.md)** if you're touching RedFlags — every non-draft RF needs **≥2 Source citations**.
- All new clinical content carries `draft: true` (or `proposed` / `partial` / `stub_full_chain`) until two of three Clinical Co-Leads sign it off (CHARTER §6.1). **Never set `reviewed: true` yourself.**
- Open a PR. CI runs `pytest`, KB validator, and RedFlag quality gates — they must stay green.

→ **[Open a content PR](https://github.com/romeo111/OpenOnco/pulls)** · see existing examples: [`multiple_myeloma.yaml`](knowledge_base/hosted/content/diseases/multiple_myeloma.yaml) (risk-stratified archetype), [`aitl.yaml`](knowledge_base/hosted/content/diseases/aitl.yaml) (etiologically-driven archetype).

### Engine, render, infrastructure

Standard PR workflow — `pytest` must pass, new code needs tests. Schema changes and spec changes require Charter §6 review. Issue templates available for ingestion adapters, render gaps, dashboard ideas.

### Become a Clinical Co-Lead

We need clinicians who can **dual-sign clinical content** so it can flip from STUB to reviewed. If you're a hematologist, oncologist, or clinical pharmacologist with sub-specialty depth (lymphoid / myeloid / solid tumors / supportive care / radiation), reach out — the sign-off workflow is async and we work around your schedule.

→ Email **[8054345@gmail.com](mailto:8054345@gmail.com)** with "OpenOnco Co-Lead" in the subject, your area, and a CV / public profile link.

### Spread the word

OpenOnco only matters if oncologists actually use it. **Star the repo, share the demo with a colleague, mention us in a tumor-board meeting**, or write about it. Every visit teaches us where the rough edges are (we read the GitHub issues and the live-demo error log).

---

## Specifications

All specifications live in [`specs/`](specs/) (Ukrainian, with English technical terms inline). **Read [`CHARTER.md`](specs/CHARTER.md) first** — it governs scope, FDA positioning, dual-review process, and what the project explicitly does **not** do.

| Spec | What it covers |
|---|---|
| [`CHARTER.md`](specs/CHARTER.md) | Governance, scope, FDA non-device CDS positioning, what we don't do |
| [`CLINICAL_CONTENT_STANDARDS.md`](specs/CLINICAL_CONTENT_STANDARDS.md) | Editorial standards: citation format, evidence levels, draft lifecycle |
| [`KNOWLEDGE_SCHEMA_SPECIFICATION.md`](specs/KNOWLEDGE_SCHEMA_SPECIFICATION.md) | KB entity schemas (Disease, Indication, Regimen, RedFlag, …) |
| [`DATA_STANDARDS.md`](specs/DATA_STANDARDS.md) | Patient-data model (FHIR R4/R5, mCODE, LOINC, ICD-O-3, RxNorm, CTCAE v5.0) |
| [`SOURCE_INGESTION_SPEC.md`](specs/SOURCE_INGESTION_SPEC.md) | Licensing, ingestion, conflict resolution, freshness, hosted vs referenced |
| [`MDT_ORCHESTRATOR_SPEC.md`](specs/MDT_ORCHESTRATOR_SPEC.md) | Tumor-board brief: roles, open questions, provenance |
| [`DIAGNOSTIC_MDT_SPEC.md`](specs/DIAGNOSTIC_MDT_SPEC.md) | Pre-biopsy mode (no histology → DiagnosticPlan, never treatment) |
| [`WORKUP_METHODOLOGY_SPEC.md`](specs/WORKUP_METHODOLOGY_SPEC.md) | Reusable methodology for any oncology domain |
| [`SKILL_ARCHITECTURE_SPEC.md`](specs/SKILL_ARCHITECTURE_SPEC.md) | MDT roles as clinically-verified skills |
| [`REFERENCE_CASE_SPECIFICATION.md`](specs/REFERENCE_CASE_SPECIFICATION.md) | The HCV-MZL "Patient Zero" reference case |
| [`REDFLAG_AUTHORING_GUIDE.md`](specs/REDFLAG_AUTHORING_GUIDE.md) | How to author a RedFlag (5-type matrix, ≥2 sources rule, golden fixtures) |
| [`CLINICAL_REVIEW_QUEUE_REDFLAGS.md`](specs/CLINICAL_REVIEW_QUEUE_REDFLAGS.md) | Open queue of RedFlag drafts awaiting clinical review |

---

## Medical disclaimer

OpenOnco is an **informational resource** to support tumor-board discussion. It is **not** a system that makes clinical decisions, **not** a medical device, and **not** for use without a qualified oncologist. Every recommendation must be verified by the treating physician with access to the full clinical picture and discussed by a multidisciplinary team. See [`specs/CHARTER.md`](specs/CHARTER.md) §11 + §15 for the full positioning statement.

---

## License

- **Code:** MIT.
- **Specifications & generated content:** CC BY 4.0.
- **Source citations** retain their original licenses — NCCN, ESMO, EHA, BSH, EASL, МОЗ України НСЗУ, etc. are **referenced, not redistributed**. See [`SOURCE_INGESTION_SPEC.md`](specs/SOURCE_INGESTION_SPEC.md) §3 for hosting modes per source.

---

## Acknowledgements

Built with: Pydantic, httpx, PyYAML, Pyodide. Standards-driven by NCCN, ESMO, EHA, BSH, EASL, МОЗ України НСЗУ, WHO Classification of Tumours 5th ed., and FDA Clinical Decision Software Guidance. Patient-data model based on HL7 FHIR R4/R5 and the mCODE implementation guide.

---

**If you're an oncologist or clinical pharmacologist:** [try the demo](https://openonco.info/try.html) on a case you know, then [open an issue](https://github.com/romeo111/OpenOnco/issues/new?labels=clinical-feedback) with what you'd change. That's the loop we're optimizing for.
