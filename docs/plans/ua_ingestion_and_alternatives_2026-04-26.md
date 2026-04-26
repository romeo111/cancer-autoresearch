# UA-specific ingestion + повна матриця альтернатив

**Дата:** 2026-04-26.
**Статус:** product + engineering plan, draft для clinical co-leads.
**Зв'язки:** SOURCE_INGESTION_SPEC §15, CHARTER §2 / §8.3 / §15 (FDA Criterion 4),
KNOWLEDGE_SCHEMA_SPECIFICATION §3 / §6, CLINICAL_CONTENT_STANDARDS §4 / §6.1.
**Memory:** `feedback_efficacy_over_registration.md` (2026-04-26 user
directive — efficacy > registration).

---

## 0. Project principle (першочергове)

> **Лікар має бачити ВСІ клінічно-релевантні альтернативи** — дорогі
> американські, незареєстровані в UA, експериментальні (clinical
> trials), reimbursed чи self-pay. UA-availability — це **анотація** до
> кожної опції, ніколи не фільтр і ніколи не downgrade-сигнал.

Цей принцип — наслідок user directive 2026-04-26 ("ефективність а не
реєстрованість"). Він є **інваріантом архітектури**, не просто
guideline. План UA-ingestion має його **захищати**, а не ламати.

### Що це конкретно означає

1. **Engine selection logic** не читає `ukraine_registration.registered`
   або `reimbursed_nszu` як вхідний сигнал. Той самий пацієнт →
   той самий `default_indication`, незалежно від UA-availability state.
2. **Render layer** показує всі альтернативи **поряд**, не приховує
   non-reimbursed і не пише "недоступно" замість назви препарату.
3. **МОЗ протоколи** — додатковий шар (UA national floor), а не
   замінник NCCN/ESMO. Останні виграють, коли є.
4. **Експериментальні опції** — first-class track у Plan, поряд зі
   standard / alternative, не глибоко-prikrytyy footnote.

---

## 1. Що план **робить уже сьогодні** (acceptance baseline)

| Componеnt | Стан | Файл/місце |
|---|---|---|
| `UkraineRegistration` schema | ✅ | `knowledge_base/schemas/base.py` |
| Drug-level annotation у render | 🟡 partial | `engine/render.py` (через notes) |
| Skeleton modules для МОЗ / НСЗУ / Держреєстр | ✅ skeletons | `knowledge_base/ingestion/{moz_extractor,nszu_loader,drlz_lookup}.py` |
| `ClinicalTrials.gov` client | ✅ implemented | `knowledge_base/clients/ctgov_client.py` |
| Per-drug `ukraine_registration.notes` | ✅ заповнюється manual | YAML drugs/ |

Щo **відсутнє** як архітектура (gaps під principle §0):

1. **Invariant** "engine не читає UA-fields як filter" — нігде не
   зафіксований у specs + немає тесту, що це порушення спалює.
2. **МОЗ Source-entity precedence policy** — невизначена. Якщо
   ingestion-агент імпортує МОЗ Indication — engine розглядає її
   рівно з NCCN/ESMO. Це деградує рекомендацію.
3. **Experimental / clinical-trial track** — `ctgov_client.py` є, але
   не приєднаний до `generate_plan()` pipeline.
4. **Access pathway entity** — для unregistered drugs (foundation /
   compassionate-use / international referral) немає first-class моделі.
5. **Cost orientation** — `typical_cost_per_cycle_uah` поле є, але
   нема механізму populate-ити автоматично + range-and-currency model.
6. **Render Access Matrix block** — таблиця з усіма альтернативами +
   реєстрацією + реімбурсом + cost + pathway не існує. Зараз info
   розкидана по `Regimen.notes` / `ukraine_availability.notes`.

---

## 2. Архітектура — нові концепти

### 2.1. AccessPathway entity (нова сутність)

Описує **як препарат / regimen фактично доступний пацієнту в Україні**,
коли він не покривається НСЗУ.

```yaml
id: PATH-LU-PSMA-INTERNATIONAL-EU
name: "Lu-177-PSMA via international referral (EU)"
name_ua: "Лютецій-177-PSMA через міжнародний реферал (ЄС)"

# Що ця pathway покриває
applies_to:
  drug_ids: [DRUG-LUTETIUM-177-PSMA]
  regimen_ids: [REG-LUTETIUM-PSMA]

pathway_type: international_referral
# Valid: foundation | compassionate_use | international_referral |
#        humanitarian_import | self_pay | clinical_trial

country_options: [DE, CZ, AT]  # ISO-3166

cost_orientation:
  currency: EUR
  per_course_min: 25000
  per_course_max: 40000
  notes: "6 циклів × 7.4 GBq; цена включає радіолабeling, госпіталізацію, supportive."

typical_lead_time_weeks: [4, 8]

contact_pattern: >
  Direct referral from oncologist to nuclear-medicine unit at participating
  EU center. Insurance pre-authorization or self-pay required.

eligibility_caveats:
  - "PSMA-PET-positive disease per VISION criteria"
  - "Post-ARPI + post-taxane (per FDA label)"
  - "Travel feasibility (6+ trips over 24 weeks)"

requires_documentation:
  - "Translated medical history + imaging"
  - "PSMA-PET on CD/DICOM"
  - "Ethics committee approval (in some destination countries)"

verified_by: null  # ID of clinical reviewer who confirmed pathway info
last_verified: null

sources: [SRC-NCCN-PROSTATE-2025]
```

**Engine semantics:** `AccessPathway` — **render-time only**. Engine
ніколи не змінює регімен/Indication через AccessPathway info.

### 2.2. CostOrientation embed (subdoc на drug)

Розширення `UkraineRegistration` ще двома range-полями:

```yaml
# на Drug.regulatory_status.ukraine_registration:
cost_uah_reimbursed:
  min: 1500
  max: 3500
  per_unit: cycle
  notes: "НСЗУ formulary 2025 Q4 tariff range"

cost_uah_self_pay:
  min: 80000
  max: 140000
  per_unit: cycle
  notes: "Drlz pharmacy survey 2026-Q1; varies by region"

cost_last_updated: "2026-01-15"
cost_source: SRC-NSZU-FORMULARY-2025-Q4
```

Обидва поля Optional. `null` означає "невідомо / not yet ingested" —
render показує дешеву placeholder "₴-? — funding pathway treba"
замість прикидатись що знає.

### 2.3. ExperimentalOption entity (новий, по аналогії з Indication)

Один-на-(disease, biomarker_profile) container для активних трайлів.
Generated, не curated:

```yaml
id: EXPER-NSCLC-EGFR-MET-1L-2026-04
applicable_to:
  disease_id: DIS-NSCLC
  molecular_subtype: EGFR_MUT
  stage_stratum: STAGE_IV_METASTATIC
  line_of_therapy: 1

trials:
  - nct_id: NCT05153486
    title: "FLAURA2: osimertinib + platinum-pemetrexed vs osimertinib"
    status: active_recruiting
    sites_ua: ["Київ — Національний інститут раку"]
    sites_global_count: 178
    inclusion_summary: "EGFR exon 19 del or L858R; treatment-naïve; ECOG 0-1"
    exclusion_summary: "Brain mets symptomatic; prior systemic for advanced disease"
    last_synced: "2026-04-26"
    sources: [SRC-CTGOV]

last_synced: "2026-04-26"
notes: >
  Auto-generated from ctgov_client query. Curator review optional but
  recommended quarterly. Ground truth: clinicaltrials.gov.
```

**Engine semantics:** `generate_plan()` після матеріалізації standard +
alternative tracks викликає `enumerate_experimental_options(disease,
biomarker_profile)` що повертає `ExperimentalOption.trials`. Render
рендерить як третій track.

### 2.4. МОЗ Source precedence policy

Додати в `Source` entity поле:

```yaml
# на Source (МОЗ-specific):
evidence_tier: 4  # national-guideline tier
precedence_policy: national_floor_only
# Valid: leading | confirmatory | national_floor_only | secondary_evidence_base

precedence_rule: >
  МОЗ Indications використовуються лише коли НЕМАЄ Tier-1/2 source
  для того самого (disease, line_of_therapy, biomarker_profile)
  scenario. Engine selection віддає перевагу NCCN/ESMO/ASCO.
```

Validator перевіряє: Indication `precedence_policy: national_floor_only`
не може бути default-Indication, якщо є paralleled Tier-1/2 Indication
для того самого scenario.

---

## 3. Engine integration

### 3.1. Plan output structure (extended)

Сьогодні `Plan` має `tracks: list[PlanTrack]` (default + alternative).
Розширюємо до:

```python
@dataclass
class Plan:
    # existing
    id: str
    patient_id: str
    tracks: list[PlanTrack]  # standard + alternative (engine-selected)

    # new
    experimental_options: list[ExperimentalOption]   # від ctgov
    access_matrix: AccessMatrix  # per-drug summary across tracks
```

`AccessMatrix` — render-time aggregation, не персистований recompute:

```python
@dataclass
class AccessMatrixRow:
    track_label: str  # "Standard" | "Alternative" | "Experimental: NCT..."
    regimen_id: str
    registered_in_ua: bool | None
    reimbursed_nszu: bool | None
    cost_orientation: CostOrientation | None
    primary_pathway: AccessPathway | None
    pathway_alternatives: list[AccessPathway]
```

### 3.2. Invariant test (CRITICAL — protects principle §0)

```python
def test_plan_independent_of_ua_availability():
    """Same patient → same default_indication regardless of which drugs
    are registered/reimbursed in Ukraine. UA-availability is render
    metadata only, never selection signal."""

    patient = _patient("patient_mm_high_risk.json")

    # Snapshot 1: всі MM drugs registered + reimbursed (поточний state)
    plan_a = generate_plan(patient, kb_root=KB_ROOT)

    # Snapshot 2: monkey-patch усі MM drugs → registered=False,
    # reimbursed_nszu=False
    with monkey_patched_ua_metadata(all_unregistered=True):
        plan_b = generate_plan(patient, kb_root=KB_ROOT)

    assert plan_a.default_indication_id == plan_b.default_indication_id
    assert plan_a.alternative_indication_id == plan_b.alternative_indication_id
    assert [t.regimen_id for t in plan_a.tracks] == \
           [t.regimen_id for t in plan_b.tracks]
```

Цей тест — **gate**. Без нього merge ingestion-роботи блокується.

### 3.3. Experimental track wiring

```python
def generate_plan(patient, kb_root) -> PlanResult:
    # ... existing standard + alternative track materialization ...

    # NEW: experimental options
    if biomarker_profile := _extract_biomarker_profile(patient, plan):
        plan.experimental_options = enumerate_experimental_options(
            disease_id=plan.disease_id,
            biomarker_profile=biomarker_profile,
            stage_stratum=plan.stage_stratum,
            line_of_therapy=plan.line_of_therapy,
            ctgov_client=ctgov,
            cache_root=KB_ROOT / "cache" / "ctgov",
            cache_ttl_days=7,
        )

    return plan
```

Якщо `ctgov_client` недоступний (offline / proxy issue) — `experimental_options=[]`,
render показує "🔬 Experimental options: дані недоступні (синхронізуйте з ClinicalTrials.gov)".
Не падає.

---

## 4. Render — новий блок "Access Matrix"

Низ Plan HTML отримує таблицю:

```html
<section class="access-matrix">
  <h2>Доступність опцій в Україні</h2>

  <table>
    <thead>
      <tr>
        <th>Опція</th>
        <th>Реєстрація UA</th>
        <th>НСЗУ</th>
        <th>Cost orientation</th>
        <th>Access pathway</th>
      </tr>
    </thead>
    <tbody>
      <tr class="track-standard">
        <td><strong>Standard:</strong> osimertinib mono</td>
        <td>✓ зареєстрований</td>
        <td>✗ out-of-pocket</td>
        <td>₴80-140K/міс</td>
        <td>
          <a href="#path-osimertinib-foundations">PATH-OSIMERTINIB-FOUNDATIONS</a>
          (Tabletochki / pharma compassionate-use)
        </td>
      </tr>
      <tr class="track-alternative">
        <td><strong>Alternative:</strong> erlotinib mono</td>
        <td>✓ generic</td>
        <td>✓ покривається</td>
        <td>₴8-12K/міс</td>
        <td>НСЗУ formulary route</td>
      </tr>
      <tr class="track-experimental">
        <td><strong>Trial:</strong> NCT05153486 (FLAURA2)</td>
        <td>n/a (трайл)</td>
        <td>n/a (трайл оплачує)</td>
        <td>0 для пацієнта</td>
        <td>Київ — Національний інститут раку</td>
      </tr>
    </tbody>
  </table>

  <p class="disclaimer">
    Інформація про ціни — orientation. Перевіряти у конкретній аптеці /
    foundation / трайл-сайті. Status updated: 2026-04-26.
  </p>
</section>
```

Стиль: A4 print-friendly, без кольорів-шумів, кожен трек чітко
розрізняється.

---

## 5. Ingestion modules — конкретні задачі

### 5.1. `nszu_loader.py` — pull state

| Задача | Estimate | Acceptance |
|---|---|---|
| Реалізувати Excel parser (openpyxl) для НСЗУ-формуляру | 2 дні | Pulls latest formulary; outputs `hosted/ukraine/nszu_formulary/<yyyy-mm>/reimbursed.yaml` |
| Diff logic month-to-month | 1 день | Identifies drugs gained/lost reimbursement; generates alert manifest |
| Cross-reference з активними Regimen-ами | 1 день | Alert: "REG-X has component DRUG-Y → DRUG-Y dropped from formulary 2026-Q3" |
| Auto-update `Drug.ukraine_registration.reimbursed_nszu` | 1 день | Idempotent; preserves manual notes; bumps `last_verified` |
| Tests | 1 день | Fixture-based (3-row Excel snapshot) |

### 5.2. `moz_extractor.py` — extract MOZ

| Задача | Estimate | Acceptance |
|---|---|---|
| PDF discovery + download | 1 день | Manual seed (`docs/sources/moz/`) + script для refresh |
| OCR (tesseract + ukr lang pack) | 2 дні | OCR'd text + confidence score per section |
| LLM-assisted structured extraction (CHARTER §8.1 OK) | 3 дні | Extract Indications + Regimens + дозування + tests; output `extracted.yaml` per Наказ |
| Manual review workflow | 1 день | `review.yaml` requires 2 clinical reviewer signoffs before promotion |
| **Tier-4 + precedence_policy enforcement** | 1 день | All MOZ-derived Indications get `precedence_policy: national_floor_only`; validator blocks default-Indication when Tier-1/2 covers |
| Tests | 2 дні | Synthetic tiny PDF; full extraction → review → promote pipeline |

### 5.3. `drlz_lookup.py` — Держреєстр

Уже 300 рядків — більш просунутий. Залишається:

| Задача | Estimate | Acceptance |
|---|---|---|
| Quarterly cron + diff | 1 день | Run script; alerts on registration changes |
| Update `Drug.ukraine_registration.registered` | already wired | — |
| Edge: drug has multiple registration numbers | 1 день | Pick most-recent; warning якщо superseded |

### 5.4. `ctgov_client.py` → `ExperimentalOption`

| Задача | Estimate | Acceptance |
|---|---|---|
| `enumerate_experimental_options(disease, biomarker_profile, …)` | 2 дні | Pure function; queries ctgov; filters by status `RECRUITING`/`ACTIVE_NOT_RECRUITING` |
| Cache layer (7-day TTL) | 1 день | `cache/ctgov/<disease>_<biomarker>_<stage>.json`; respects ctgov rate limits |
| UA-site enrichment | 1 день | Parses `LocationFacility` field, surfaces UA cities |
| Tests | 1 день | Mocked ctgov response; deterministic output |

### 5.5. `AccessPathway` content

| Задача | Estimate | Acceptance |
|---|---|---|
| Schema + Pydantic model | 1 день | `knowledge_base/schemas/access_pathway.py` |
| Initial seed: ~30 pathways for top non-reimbursed drugs | 5 днів clinical authoring | T-DXd / CDK4/6i / Lu-PSMA / sacituzumab / talazoparib / niraparib / dostarlimab / EV / etc. |
| Render integration | 1 день | Linked from Access Matrix table |

### 5.6. Cost orientation — populate

| Задача | Estimate | Acceptance |
|---|---|---|
| Schema extension (CostRange embed) | 1 день | Pydantic + render |
| НСЗУ-derived `cost_uah_reimbursed` | 0 (auto з §5.1) | — |
| Manual `cost_uah_self_pay` seeding for top-30 expensive drugs | 3 дні clinical/admin | One-time bootstrap; range estimates with sources |

---

## 6. Принципи governance (CHARTER §6.1 + §8.3 compliance)

1. **Кожна ingestion-derived зміна → ProvenanceEvent** в `events.jsonl`.
   "DRUG-OSIMERTINIB lost reimbursement 2026-Q3 per НСЗУ formulary
   parse" — це event, не silent overwrite.
2. **Manual seed для AccessPathway та non-reimbursed cost** — потребує
   clinical/admin reviewer signoff (2 reviewers per CHARTER §6.1) перед
   merge у KB.
3. **МОЗ extraction LLM-output** — обов'язковий human verification per
   CHARTER §8.1; Pydantic validation + "draft: true" доти, поки не
   reviewed.
4. **Stale-data display rule** — якщо `cost_last_updated` старіший за
   180 днів → render показує "⚠ orientation may be outdated; verify"
   замість мовчазного показу.

---

## 7. Phasing

### Phase A — Architectural invariant (foundation)

**Виконати першим. Без цього все наступне ризикує деградувати продукт.**

1. PROPOSAL у `SOURCE_INGESTION_SPEC.md` §15a: "UA-availability is
   annotation, never filter".
2. Invariant test `test_plan_independent_of_ua_availability` (§3.2).
3. Schema: `Source.precedence_policy` field; validator gate (§2.4).
4. Manual seed: position МОЗ Source entities як `precedence_policy:
   national_floor_only` (3-5 існуючих МОЗ sources).

Estimate: **~3 дні**. **Critical path** — блокує merge всього інакшого.

### Phase B — НСЗУ + Drlz auto-refresh

Замикає current-state metadata loop. Без цього `reimbursed_nszu` /
`registered` дрейфують вручну.

1. `nszu_loader.py` real implementation (§5.1).
2. `drlz_lookup.py` quarterly cron (§5.3).
3. Auto-update + ProvenanceEvent log on changes.

Estimate: **~7 днів**.

### Phase C — Experimental track

Найбільший delta для product principle §0. Лікар бачить трайли поряд
з SoC.

1. `ctgov_client.py` → `enumerate_experimental_options` (§5.4).
2. `ExperimentalOption` schema + plan integration (§2.3 + §3.3).
3. Render: experimental track як third column в tracks section.

Estimate: **~5 днів**.

### Phase D — AccessPathway + Cost orientation

Закриває "якщо не реєстрований — то як його взагалі дістати" gap.

1. `AccessPathway` schema + 30-pathway seed (§5.5).
2. `CostOrientation` embed + НСЗУ-derived auto-populate (§5.6).
3. Render Access Matrix block (§4).

Estimate: **~10 днів**.

### Phase E — МОЗ extraction (highest-effort, lowest-immediate-value)

Робити **останнім**, бо МОЗ data є supplementary, не replacement. Без
nego всі попередні phases вже працюють на NCCN/ESMO + ingested
metadata.

1. `moz_extractor.py` real OCR + LLM extraction (§5.2).
2. Tier-4 enforcement (вже зроблено в Phase A).
3. Initial 3-5 МОЗ протоколів через extraction → review → merge pipeline.

Estimate: **~10 днів** (більшість — clinical review iteration).

**Total estimate: ~35 днів wall-clock.** Phases A-D без E дають 80%
value за ~25 днів.

---

## 8. Acceptance criteria (overall)

Phase plan complete коли:

1. **Invariant test зелений** — `test_plan_independent_of_ua_availability`.
2. **Plan HTML містить Access Matrix block** для будь-якого пацієнта,
   у якому є хоча б один non-reimbursed drug у tracks.
3. **Experimental track появляється** для biomarker-driven диseases
   (NSCLC EGFR/ALK/etc., melanoma BRAF, RCC clear-cell, breast HER2+,
   prostate BRCA) коли є matching active recruiting trial.
4. **АT-least один реальний alert** з НСЗУ diff workflow за реальний
   місяць (after deploy) — proof-of-life monitoring.
5. **Drlz registration changes** пишуть ProvenanceEvent у audit log.
6. **МОЗ-derived Indication ніколи не виграє** над NCCN/ESMO для того
   самого scenario — validator-enforced.
7. **Render показує "stale orientation" warning**, якщо cost data >180
   днів — protects against silent confidence in outdated numbers.

---

## 9. Ризики і чесні compromise-и

### Ризик: ctgov rate limits + UA-site mismatch

ClinicalTrials.gov не завжди має точний статус UA-сайтів. Може
показати трайл як "RECRUITING" коли UA-сайт фактично closed.

**Compromise:** render показує trial з warning "verify enrollment
status with site contact"; cache 7-day TTL зменшує rate burn але не
fixит ground-truth lag. Лікар має фінальну відповідальність verify.

### Ризик: МОЗ накази нерегулярно публікуються

Ingestion cadence не може бути точніше за упload-cadence МОЗ. Може
бути 6 місяців тиші → раптом 3 нові накази.

**Compromise:** manual discovery (script повідомляє про нові PDFs); НЕ
auto-pulling — щоб OCR + LLM extraction завжди йшли з human in the
loop. Додатково: alert при новому Наказі де згадано вже-існуючий
Drug у KB.

### Ризик: cost orientation швидко стає несвіжим

Pharmacy retail prices в Україні плавають з ринковими подіями. ₴-діапазон
2026-Q1 може бути irrelevant у 2026-Q3.

**Compromise:** `cost_last_updated` обов'язкове; render warning при
>180 днів; quarterly review cron для top-30 drugs (manual update).

### Ризик: AccessPathway info "застаріла"

Foundations змінюють criteria, compassionate-use programs закриваються,
EU-центри змінюють приймання UA-патієнтів.

**Compromise:** `verified_by` + `last_verified` обов'язкові; quarterly
review cron; render warning "verify with foundation directly".

### Ризик: повна Access Matrix перевантажує plan HTML

Plan вже ~26KB; додавання матриці ще ~5-10KB. Лікар може заплутатися
у рясноти інформації.

**Compromise:** Access Matrix collapsable "▶ Доступність в Україні"
або окремий tab у render. Default-collapsed для standard cases, auto-
expanded коли `≥1 регімен має non-reimbursed component`.

---

## 10. Open clinical questions (для co-leads)

1. **AccessPathway content** — хто аuth'ор? Один person або
   distributed list of foundations / international centers contributors?
2. **Cost orientation freshness threshold** — 180 днів OK як warning
   trigger? Чи треба коротший (90)?
3. **МОЗ Indication promotion** — який порядок? Завжди потребує
   `Tier-1/2` confirmatory citation, чи МОЗ-only OK для UA-specific
   scenarios (e.g., етап локального доступу)?
4. **Experimental track patient eligibility filter** — engine
   автоматично filter-ить трайли за inclusion criteria patient profile?
   Чи показуємо все що active, лікар сам вирішує?
5. **Stigma питання** — чи треба гідно показувати foundation pathways?
   Деякі лікарі вважають foundations "соромними" для продукту.

---

## 11. Recommended first PR

(Per плана §7 Phase A — критично-шляховий blocker.)

1. Add `tests/test_plan_invariant_ua_availability.py` — invariant test
   (skipped initially, marked `xfail`, until we wire it).
2. Add `Source.precedence_policy` field + Pydantic validation.
3. Annotate існуючих МОЗ Sources (`SRC-MOZ-UA-LYMPH-2013`,
   `SRC-MOZ-UA-CLL-2022`) з `precedence_policy: national_floor_only`.
4. Validator extension: block default-Indication, що cite-ить
   national-floor-only source AND has paralleled Tier-1/2 source.
5. Doc the invariant у `SOURCE_INGESTION_SPEC.md` §15a.

Це ~2-3 дні роботи, не змінює engine logic, лише фіксує invariant у
schema-and-test layer. Після цього merge — далі phases B/C/D/E
паралельно і безпечно.
