# Regimen Phases Refactor — план

**Дата:** 2026-04-28
**Статус:** план узгоджено, до коду не приступали
**Тригер:** діагностичне питання користувача — "якщо лікар пропонує ендоксан перед основною терапією — чому наш план не передбачив ці ліки?"

## 1. Проблема

При аналізі нульового кейсу виявлено, що рекомендація додати циклофосфамід ("ендоксан") *перед* основною терапією — типовий клінічний сценарій (lymphodepletion перед CAR-T/TIL, bridging therapy, метрономна Treg-депleція перед ICI, кондиціонування перед ТКМ, день 1 стандартного протоколу) — у згенерованому плані не з'являється як окрема видима фаза. Чотири структурні причини:

1. **`Regimen` schema не має поняття "фаз".** Тільки плоский `components` + рядковий `premedication`. Lymphodepletion для axi-cel у `reg_car_t_axicel.yaml` зараз продубльована між цими полями зі сноскою-обхідним шляхом курaтора.
2. **Bridging therapy існує тільки як проза в `notes`.** Немає поля `bridging_options: list[regimen_id]`. У CAR-T/TIL регіменах "bridging permitted" згадано прозою.
3. **Метрономний Cy + ICI / Treg-депleція як стратегія в KB не моделюється.** Грep `metronomic|treg|low.dose` по `hosted/content` — жодної індикації цього типу. Лікар, що пропонує цю стратегію, виходить за межі структурованих рекомендацій rule-engine.
4. **Render злиплює lymphodepletion у деталі регімена.** `_render_pretreatment_investigations` стосується діагностичного workup, не пре-терапевтичних препаратів. Окремої секції "Перед основною терапією" нема.

## 2. Контекст у спеці

`specs/KNOWLEDGE_SCHEMA_SPECIFICATION.md`:
- `Indication.phases` — вже специфіковано (рядки 1565-1676) для секвенцій типу neoadjuvant→surgery→adjuvant. **Це між-модальні фази, не intra-regimen.**
- `MonitoringSchedule` лінкується на "Regimen + Phase" (рядок 104) — концепт "фази" вже дотичний до Regimen, але як зовнішнє посилання, не як власна структура.
- `Regimen.phases` — **відсутнє.** Це структурна прогалина.

## 3. Узгоджені рішення (5 пунктів)

| # | Питання | Рішення |
|---|---|---|
| 1 | Один атомарний PR чи два кроки? | **Two-step:** (a) schema + loader auto-wrap (back-compat noop), (b) render + ручна YAML-міграція |
| 2 | Гілка від `master` чи від поточної? | Від `master` |
| 3 | Citations API верифікатор у тому ж PR? | **Розділити** — окрема гілка `feat/citation-verifier`, окремий ризик |
| 4 | Anthropic API key у CI доступний? | Є → Citations API верифікатор стає must-have, не nice-to-have |
| 5 | Список ручної міграції потребує перевірки? | Так → перевірено, виявлено 18 файлів, не 10-15 |

## 4. Структурний рефактор — пропонована схема

### 4.1. `RegimenPhase` (нова сутність)

```python
class RegimenPhase(Base):
    name: str
    # дозволені значення: "lymphodepletion" | "bridging" | "induction"
    # | "consolidation" | "maintenance" | "main" | "premedication"
    # | "conditioning" | "salvage_induction" | "alternating_block_a"
    # | "alternating_block_b" | "il2_support"
    purpose_ua: str  # "виснаження лімфоцитів перед CAR-T для приживлення клітин"
    purpose_en: Optional[str] = None
    components: list[RegimenComponent]
    duration: Optional[str] = None  # "3 days, days -5 to -3"
    timing_relative_to: Optional[str] = None
    # "main_infusion" | "next_phase" | "absolute" | "previous_phase_completion"
    timing_offset_days: Optional[int] = None  # -5 = "5 days before main"
    optional: bool = False  # bridging — optional; lymphodepletion — required
    sources: list[str] = Field(default_factory=list)
```

### 4.2. Розширення `Regimen`

```python
class Regimen(Base):
    # ... existing fields ...
    phases: list[RegimenPhase] = Field(default_factory=list)
    bridging_options: list[str] = Field(default_factory=list)
    # regimen_ids of acceptable bridging regimens during manufacturing window
```

### 4.3. Loader auto-wrap (back-compat)

При завантаженні YAML, де `phases: []` і `components: [...]`:
```python
if not regimen.phases and regimen.components:
    regimen.phases = [RegimenPhase(
        name="main",
        purpose_ua="основна терапія",
        components=regimen.components,
    )]
```
Це гарантує: жоден існуючий YAML не падає, жоден існуючий звіт не змінюється до моменту ручної міграції конкретного файла.

### 4.4. `Indication.kind` — новий enum

```python
class IndicationKind(str, Enum):
    standard = "standard"  # реєстрована основна терапія (default)
    bridging = "bridging"  # bridging chemo до CAR-T/TIL
    immunomod_pretreatment = "immunomod_pretreatment"  # off-label метрономний Cy + ICI
    supportive = "supportive"
```

`Indication.kind = "immunomod_pretreatment"` рендериться окремим банером:
> "Це off-label стратегія, поза структурованими рекомендаціями rule-engine.
> Клінічна оцінка обов'язкова. CHARTER §8.3."

Закриває причину #3 чесно: ми не *рекомендуємо* off-label стратегію, ми *описуємо її контекст*, якщо лікар запропонував.

### 4.5. Render — `_render_treatment_phases(regimen)`

Кожна фаза → окремий видимий блок із заголовком `purpose_ua`:

```
┌─ Перед основною терапією: lymphodepletion ────────┐
│ Циклофосфамід 500 мг/м² IV дні -5, -4, -3         │
│ Флюдарабін 30 мг/м²  IV дні -5, -4, -3            │
│ Мета: виснаження лімфоцитів перед CAR-T           │
└────────────────────────────────────────────────────┘

┌─ Основна терапія: Аxі-cel CAR-T інфузія ──────────┐
│ ...                                                │
└────────────────────────────────────────────────────┘
```

Lymphodepletion перестає ховатись — закриває причину #4. `bridging_options` рендериться окремою секцією "Якщо очікування на основну терапію >2 тижні" — закриває причину #1.

## 5. План міграції — 18 ручних YAML

### Група A — Lymphodepletion + main infusion (5 файлів)

| Файл | Фази після міграції |
|---|---|
| `reg_car_t_axicel.yaml` | lymphodepletion (Cy+Flu) → main_infusion (axi-cel) |
| `reg_car_t_axicel_fl.yaml` | те саме |
| `reg_car_t_axicel_hgbl.yaml` | те саме |
| `reg_car_t_brexucel_mcl.yaml` | те саме |
| `reg_tisagenlecleucel_b_all.yaml` | те саме |

### Група B — TIL з трьома фазами (1)

| Файл | Фази |
|---|---|
| `reg_lifileucel_til_melanoma.yaml` | lymphodepletion → main_infusion → il2_support |

### Група C — Induction → autoSCT (4)

| Файл | Фази |
|---|---|
| `r_dhap_autosct.yaml` | salvage_induction → conditioning → autoSCT |
| `reg_rdhap_burkitt.yaml` | те саме |
| `reg_rice_burkitt.yaml` | те саме |
| `reg_r_ice_pmbcl.yaml` | те саме |

### Група D — Induction → conditioning → alloSCT (4)

| Файл | Фази |
|---|---|
| `reg_choep_allosct_consolidation.yaml` | induction → conditioning → alloHCT |
| `reg_allohct_pmf.yaml` | conditioning → alloHCT |
| `reg_allohct_mds_hr.yaml` | те саме |
| `reg_allohct_cml_advanced.yaml` | те саме |

### Група E — Multi-block / alternating intensive chemo (4)

| Файл | Фази |
|---|---|
| `hyper_cvad_r.yaml` | alternating_block_a (Cy+vinc+doxo+dexa) / alternating_block_b (MTX+ARA-C) × 8 |
| `codox_m_ivac.yaml` | alternating CODOX-M / IVAC blocks |
| `matrix.yaml` | induction (PCNSL) → передає в окремий autoSCT-регімен |
| `smile.yaml` | multi-block NK/T induction |

### Не мігрується (явно)

- Maintenance-only регімени (`*_maintenance_*.yaml`, ~10 шт) — loader обгорне в `phases: [{name: "maintenance"}]` автоматично
- 1L chemo з циклами 1-6 (`r_chop`, `pola_r_chp`, `da_epoch_r`, …) — однофазні у нашому сенсі
- ICI / TKI / ендокринні моно-режими (~40) — однофазні за визначенням

### Перехресні залежності
- Indication-файли, що референсять CAR-T (`ind_dlbcl_3l_axicel_cart`, `ind_fl_3l_axicel_cart`, `ind_hgbl_dh_2l_cart_axicel`, `ind_b_all_3l_tisagenlecleucel`, `ind_mcl_3l_brexucel_cart`, `ind_dlbcl_3l_liso_cel_cart`, `ind_mm_4l_ciltacel_cart`, `ind_melanoma_3l_lifileucel`) — після міграції regimенів додати їм `bridging_options: [...]`. ~8 Indication YAML, дрібні правки.
- Render golden fixture: новий fixture для axi-cel, що перевіряє наявність окремого блоку lymphodepletion у HTML.

## 6. Алгоритми проти неверифікованих відповідей — окрема гілка `feat/citation-verifier`

Шість прийомів, відсортовані за ROI. Перші три — must-have.

| # | Прийом | Кошт | ROI |
|---|---|---|---|
| 1 | **Cite-or-strip at render.** Render-guard: будь-яке поле, що йде в HTML, має трасуватись до ≥1 валідного `source_refs[]`. Інакше — strip + badge "❓ без цитати". | ~1 день | High |
| 2 | **Schema-completeness gate.** Pre-commit + CI: будь-яка `Regimen` зобов'язана мати `phases` або `components` непорожні. `Indication.kind = immunomod_pretreatment` зобов'язана нести `actionability_review_required: true`. | Кілька годин | High |
| 3 | **[Anthropic Citations API](https://docs.anthropic.com/en/docs/build-with-claude/citations) як верифікатор.** Скрипт `scripts/verify_citations.py` бере чорнову Indication / BMA + цитовані PDF Sources, пропускає через Citations API, повертає grounded/ungrounded. Незаземлені → `actionability_review_required: true`. **LLM-як-перевіряч, не вирішувач (CHARTER §8.3 чистий).** | 2-3 дні | High |
| 4 | **Chain-of-Verification (CoVe, [Dhuliawala 2023](https://arxiv.org/abs/2309.11495))** на Phase 3 BMA reconstruction. Чернетка → перевірочні питання → відповіді з первинних Sources → ревізія. -30-50% hallucination на listing-задачах у літературі. Уже частково в льоті (commit `e31ebd1`). | 1-2 дні | Medium |
| 5 | **Two-agent disagreement-as-flag.** Структуровані мітки (CIViC level, evidence direction, BMA category) проганяються двічі різними промптами. Розбіг → автоматично `actionability_review_required: true`. SelfCheckGPT-варіація ([Manakul 2023](https://arxiv.org/abs/2303.08896)). | 1 день | Medium |
| 6 | **Constrained vocabulary at draft generation.** LLM-drafter отримує системний промпт із дозволеним списком `drug_id` / `biomarker_id` / `source_id` з KB. Drug, якого нема — drafter зобов'язаний створити чернетку Drug-сутності, не вигадати назву. | <1 день | Low (запобігає рідкісному кейсу, але важливому) |

## 7. Tradeoffs / ризики

- **Розмір рефактора:** schema + loader + render + ~18 ручних YAML + спека = великий PR. Two-step розбиває на dvа commit'и: schema+loader (back-compat noop) → render + ручна міграція. Рекомендовано two-step навіть попри запит "одним рефактором".
- **Спека:** `KNOWLEDGE_SCHEMA_SPECIFICATION.md` §6 (Regimen) — додати `phases`, `bridging_options`. Створити §6.X для `IndicationKind`. Дозволено редагувати специфікацію (CLAUDE.md §"What Claude Code should do"), після твого окремого ОК на текст.
- **Зворотна сумісність:** `components` лишається. Жоден існуючий YAML не падає, жоден HTML-звіт не змінюється до моменту ручної міграції відповідного файла.
- **CHARTER §6.1 dev-mode exemption:** активний у v0.1 → один Co-Lead достатньо для більшості. CAR-T/TIL/SCT міграція (10 файлів Групи A-D) — high-stakes, рекомендую двох рев'юерів попри exemption.
- **Бюджет API:** Citations API + CoVe на 399 BMA → терпимо (Phase 3-N уже витрачає бюджет).

## 8. Послідовність робіт

1. **PR1 (`feat/regimen-phases-refactor` від `master`):** schema + loader auto-wrap + golden fixture для axi-cel. Back-compat noop. Один логічний commit.
2. **PR2 (та сама гілка, після PR1):** ручна міграція 18 YAML-файлів (Групи A-E) + render `_render_treatment_phases` + оновлення спеки + bridging_options на 8 Indication-файлах.
3. **PR3 (`feat/citation-verifier` від `master`):** алгоритми #1-3 (cite-or-strip, schema gate, Citations API верифікатор).
4. **PR4 (`feat/citation-verifier`, після PR3):** алгоритми #4-6 (CoVe, two-agent, constrained vocab).

PR1 і PR3 можна вести паралельно (різні гілки, не перетинаються).

## 9. Що чекає на сигнал перед кодом

- Коли стартувати PR1.
- Чи дозволяю редагувати `KNOWLEDGE_SCHEMA_SPECIFICATION.md` як частину PR1, чи окремим pre-PR.
- Чи треба окремо обговорити вибір моделей для Citations API (Sonnet 4.6 / Opus 4.7) до PR3.
