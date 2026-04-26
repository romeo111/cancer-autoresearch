# OpenOnco

> **Open-source clinical decision support for oncology tumor boards.**
> Upload a patient profile → get two alternative treatment plans
> (standard + aggressive), side by side, with every recommendation cited.
> Plans refresh as new data arrives. All clinical logic lives in a
> declarative rule engine over a curated knowledge base — **no LLM
> picks regimens** (CHARTER §8.3).

**Live demo:** **[openonco.info](https://openonco.info)** — try it in the browser, no install needed.
**Specifications-first:** every clinical statement traceable to a Source entity; dual clinical-lead review per [CHARTER §6.1](specs/CHARTER.md).
**FDA non-device CDS positioning** per [CHARTER §15](specs/CHARTER.md) — informational support tool, not a medical device.
**License:** Code MIT · Content / specs CC BY 4.0.

---

## Why this exists

Picking a regimen for a real patient is **2–4 hours of manual desk work**: open NCCN PDF, cross-check ESMO, re-read the local МОЗ protocol, verify formulary reimbursement, look up renal/hepatic dose adjustments, layer supportive care, remember vaccinations and OI prophylaxis. Every patient. One missed contraindication can be fatal.

OpenOnco automates the chore work. The clinician gets a **drafted plan with every citation already attached** and only verifies / tailors it. The logic mirrors a **classical multidisciplinary tumor board (MDT)** — each "virtual specialist" is a versioned rule module with its own sources and `last_reviewed` stamp.

---

## Status

**v0.1.0-alpha — first public alpha.** Specifications complete; knowledge base, rule engine, render layer, sign-off infrastructure, and in-browser Pyodide demo all functional and exercised by 1450+ tests.

**Knowledge base** (Pydantic-validated; minor ref drift on in-flight NSCLC scaffolding being closed out):

| | Count |
|---|---:|
| Total entities | **1923** |
| Diseases | 65 (lymphoid + myeloid + solid tumors scaffolded) |
| Indications | 250 |
| Algorithms | 95 |
| Regimens | 186 |
| RedFlags | 313 (≥2 sources each per REDFLAG_AUTHORING_GUIDE) |
| Drugs | 185 (NSZU registration / reimbursement verified) |
| BiomarkerActionability cells | 399 (ESCAT / OncoKB tier mapping) |
| Biomarkers / genes | 97 |
| Tests / procedures | 95 |
| Sources | 162 (≈10,200 guideline pages, 26,000+ primary publications referenced) |

**Engine** — rule-based decision engine with ESCAT / OncoKB tier interpretation, NSZU availability badges, patient-mode rendering, plan revisions / supersedes loop, append-only reviewer event log, QR-code case-token sharing. Bundle: split core (~1.4 MB) + per-disease lazy-load; ~2.4 MB compressed for the Pyodide demo.

**Sign-off infrastructure** — CLI + dashboard + JSONL audit log + render badges (CHARTER §6.1). Currently 15 / 202 clinical units carry ≥2 reviewer sign-offs; the rest render with the **STUB** badge by design until two of three Clinical Co-Leads sign off.

→ Live KB metrics, per-disease coverage, sign-off ratio: [openonco.info/capabilities](https://openonco.info/capabilities.html)

---

## What it does

- **Two-track plan generator (CHARTER §2).** Always ≥2 alternative tracks side by side — never a single "system-prescribes-X" output. Each track ships rationale, red-flag triggers, hard contraindications, supportive care, monitoring schedule, sourced outcome numbers, and a "what NOT to do" list per indication.
- **Versioned skill registry (16 MDT specialists).** Hematology, hematopathology, ID/hepatology, radiology, molecular genetics, clinical pharmacy, radiation oncology, surgical oncology, transplant, CAR-T, psychology, palliative, social work, primary care, medical oncology, pathology — each a versioned rule bundle with `last_reviewed`, `clinical_lead`, `verified_by` sign-offs.
- **Diagnostic-phase MDT (CHARTER §15.2 C7).** No histology → Workup Brief, never a treatment Plan. Mechanical hard gate.
- **Plan revisions / supersedes loop.** `revise_plan(...)` polymorphic across `diagnostic→diagnostic`, `diagnostic→treatment` (promotion), and `treatment→treatment`; refuses illegal downgrade. Immutable audit chain (CHARTER §10.2).
- **Append-only reviewer event log.** `confirmed` / `modified` / `approved` / `rejected` events persist as JSONL and rehydrate into the next render — full audit trail per CHARTER §10.2 / §15.1 Criterion 4.
- **ESCAT / OncoKB actionability.** 399 BiomarkerActionability cells map biomarker × disease × drug to evidence tiers, surfaced as render badges.
- **FDA Criterion 4 metadata on every Plan.** `intended_use`, `hcp_user_specification`, `patient_population_match`, `algorithm_summary`, `data_sources_summary`, `data_limitations`, `automation_bias_warning`, `time_critical`. Full algorithm decision trace embedded.
- **HTML render layer.** Single-file A4-printable HTML per Plan / Diagnostic Brief / Revision Note. Patient-mode and HCP-mode. UA / EN via `target_lang`. NSZU availability badges per drug.
- **In-browser Pyodide demo.** The actual Python engine runs in the browser at [openonco.info/try.html](https://openonco.info/try.html) — no backend, no patient data leaves the device.

---

## Try it

**End users / clinicians:** **[openonco.info/try.html](https://openonco.info/try.html)** — paste a patient JSON profile and the Pyodide-loaded engine generates a treatment plan with ESCAT / OncoKB tier badges, NSZU availability badges, and patient-mode rendering. No installation required, no PHI server-side (CHARTER §9.3).

Sample patients: **[openonco.info/gallery.html](https://openonco.info/gallery.html)** — 30+ pre-rendered cases across DLBCL, FL, CLL/SLL, MCL, HCV-MZL, HCL, WM, HGBL-DH, PTCL, ALCL, AITL, MF/Sézary, cHL, NLPBL, and MM.

**Contributors:** start with [`specs/`](specs/) and [`CLAUDE.md`](CLAUDE.md) — these define scope, schemas, and authoring conventions before any KB or code change.

**Developers running tests locally:**

```bash
git clone https://github.com/romeo111/OpenOnco.git
cd OpenOnco
pip install -e .
pytest tests/
```

Python 3.11+ required.

---

## Repository layout

```
openonco/
├── specs/                  # 14+ specifications (UA primary)
├── knowledge_base/
│   ├── schemas/            # Pydantic schemas
│   ├── engine/             # rule engine, MDT, render, revisions, events
│   ├── validation/         # YAML loader + ref-integrity checker
│   ├── clients/            # source-API + translate clients
│   ├── stats.py            # KB info dashboard
│   └── hosted/content/     # YAML knowledge base
├── examples/               # synthetic patient profiles
├── scripts/build_site.py   # static-site builder (GitHub Pages)
├── docs/                   # generated site → openonco.info
│   └── plans/              # partnership / pitch deliverables
├── tests/                  # pytest suite (1450+ tests)
└── legacy/                 # retired autoresearch pipeline (archival only)
```

---

## How to contribute

**Try it and tell us what's wrong.** A clinician's eye on a rendered Plan is the most valuable contribution right now. Try the [demo](https://openonco.info/try.html) on a case you know, then **[open a clinical-feedback issue](https://github.com/romeo111/OpenOnco/issues/new?labels=clinical-feedback)** — even one line ("this regimen is missing the CrCl <30 dose adjustment") helps.

**Add a disease or fix a regimen.** KB is YAML under `knowledge_base/hosted/content/`. Read [`specs/CLINICAL_CONTENT_STANDARDS.md`](specs/CLINICAL_CONTENT_STANDARDS.md) for citation format and [`specs/REDFLAG_AUTHORING_GUIDE.md`](specs/REDFLAG_AUTHORING_GUIDE.md) for RedFlags (≥2 Source citations required). New clinical content stays `draft` / `proposed` / `partial` / `stub_full_chain` until two of three Clinical Co-Leads sign off (CHARTER §6.1) — **never set `reviewed: true` yourself.** CI runs `pytest`, KB validator, and RedFlag quality gates.

**Engine / render / infrastructure.** Standard PR — `pytest` must pass, new code needs tests. Schema and spec changes go through CHARTER §6 review.

**Become a Clinical Co-Lead.** Hematology / oncology / clinical pharmacology sub-specialty depth needed to dual-sign content out of STUB. Email **[8054345@gmail.com](mailto:8054345@gmail.com)** with "OpenOnco Co-Lead", your area, and a CV / public profile link.

---

## Specifications

All 14+ specifications live in [`specs/`](specs/) (Ukrainian, English technical terms inline). **Read [`CHARTER.md`](specs/CHARTER.md) first** — it governs scope, FDA positioning, dual-review process, and what the project explicitly does **not** do.

Key specs: [`CLINICAL_CONTENT_STANDARDS`](specs/CLINICAL_CONTENT_STANDARDS.md) (citation format, evidence levels, draft lifecycle) · [`KNOWLEDGE_SCHEMA_SPECIFICATION`](specs/KNOWLEDGE_SCHEMA_SPECIFICATION.md) (entity schemas) · [`DATA_STANDARDS`](specs/DATA_STANDARDS.md) (FHIR R4/R5, mCODE, LOINC, ICD-O-3, RxNorm, CTCAE v5.0) · [`SOURCE_INGESTION_SPEC`](specs/SOURCE_INGESTION_SPEC.md) (licensing, hosted vs referenced) · [`MDT_ORCHESTRATOR_SPEC`](specs/MDT_ORCHESTRATOR_SPEC.md) · [`DIAGNOSTIC_MDT_SPEC`](specs/DIAGNOSTIC_MDT_SPEC.md) (pre-biopsy mode) · [`SKILL_ARCHITECTURE_SPEC`](specs/SKILL_ARCHITECTURE_SPEC.md) · [`REDFLAG_AUTHORING_GUIDE`](specs/REDFLAG_AUTHORING_GUIDE.md).

---

## Recent work (2026-04 sprint)

- **CSD-1..6** ([`docs/plans/`](docs/plans/)) — partnership / pitch pack: demo report, NSZU verification audit (167 drugs, 100% verified), patient-mode demo, OncoKB integration + safe rollout design, source-freshness audit, engine-bundle profiling.
- **PROD-1..5** — engine-bundle split (core + per-disease lazy-load), patient-mode rendering, ESCAT/OncoKB and NSZU render badges, QR-code case-token sharing.
- **RedFlag quality phases 1-7** — 313 RFs, ≥2 sources each, golden fixtures, RF tests green.
- **Site polish** — favicon (Rod of Asclepius), Playfair Display Cyrillic font, /try.html example loader UX synced with questionnaires.

---

## Medical disclaimer

OpenOnco is an **informational resource** to support tumor-board discussion. It is **not** a system that makes clinical decisions, **not** a medical device, and **not** for use without a qualified oncologist. Every recommendation must be verified by the treating physician with access to the full clinical picture and discussed by a multidisciplinary team. See [`specs/CHARTER.md`](specs/CHARTER.md) §11 + §15 for the full positioning statement.

---

## License

- **Code:** MIT.
- **Specifications & generated content:** CC BY 4.0.
- **Source citations** retain their original licenses — NCCN, ESMO, EHA, BSH, EASL, МОЗ України НСЗУ, etc. are **referenced, not redistributed** (CHARTER §2 non-commercial scope; many source licenses depend on this). See [`SOURCE_INGESTION_SPEC.md`](specs/SOURCE_INGESTION_SPEC.md) §3 for hosting modes per source.

---

## Acknowledgements

Built with Pydantic, httpx, PyYAML, Pyodide. Standards-driven by NCCN, ESMO, EHA, BSH, EASL, МОЗ України НСЗУ, WHO Classification of Tumours 5th ed., FDA CDS Guidance, HL7 FHIR R4/R5, mCODE.

---

**Oncologist or clinical pharmacologist?** [Try the demo](https://openonco.info/try.html) on a case you know, then [open an issue](https://github.com/romeo111/OpenOnco/issues/new?labels=clinical-feedback) with what you'd change. That's the loop we're optimizing for.
