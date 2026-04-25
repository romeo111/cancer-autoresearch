# OpenOnco

Вільний інформаційний ресурс для підтримки клінічних рішень в онкології:
завантажити профіль пацієнта → отримати два плани лікування
(стандартний + агресивний) з повним цитуванням джерел. Плани
автоматично оновлюються при отриманні нових даних.

**Статус:** v0.1 draft. Специфікації написані; rule engine + MDT
Orchestrator + Decision Provenance працюють на reference-кейсі (HCV-MZL).
Контент-сторона (Indication-и з підписами клінічних рев'юєрів) — у роботі.

## Де що

- [`specs/`](specs/) — активні специфікації проєкту:
  - [`CHARTER.md`](specs/CHARTER.md) — governance, scope, FDA non-device CDS positioning
  - [`CLINICAL_CONTENT_STANDARDS.md`](specs/CLINICAL_CONTENT_STANDARDS.md) — редакційні стандарти клінічного контенту
  - [`KNOWLEDGE_SCHEMA_SPECIFICATION.md`](specs/KNOWLEDGE_SCHEMA_SPECIFICATION.md) — схема бази знань (rule engine)
  - [`DATA_STANDARDS.md`](specs/DATA_STANDARDS.md) — модель пацієнтських даних (FHIR R4/R5, mCODE)
  - [`REFERENCE_CASE_SPECIFICATION.md`](specs/REFERENCE_CASE_SPECIFICATION.md) — reference clinical case (HCV-MZL)
  - [`SOURCE_INGESTION_SPEC.md`](specs/SOURCE_INGESTION_SPEC.md) — ліцензування, ingestion, conflict resolution, freshness
  - [`MDT_ORCHESTRATOR_SPEC.md`](specs/MDT_ORCHESTRATOR_SPEC.md) — tumor-board brief: ролі, відкриті питання, decision provenance
  - [`DIAGNOSTIC_MDT_SPEC.md`](specs/DIAGNOSTIC_MDT_SPEC.md) — pre-biopsy режим (без гістології → DiagnosticPlan, не Plan лікування)
- [`knowledge_base/`](knowledge_base/) — Pydantic-схеми, HCV-MZL seed, rule engine
  (`engine/`: plan, diagnostic, mdt_orchestrator, provenance, revisions, persistence),
  CLI (`python -m knowledge_base.engine.cli`)
- [`legacy/`](legacy/) — попередня autoresearch-версія, retired 2026-04-24. Див. [`legacy/README.md`](legacy/README.md).

## Medical disclaimer

Цей проєкт — інформаційний ресурс для підтримки обговорення в тумор-борді,
**не система, що приймає клінічні рішення**. Всі рекомендації потребують
перевірки лікуючим лікарем з доступом до повної клінічної картини пацієнта
і обговорення мультидисциплінарною командою. Деталі — у
[`specs/CHARTER.md`](specs/CHARTER.md) §11.

## License

Code: MIT · Specifications / content: CC BY 4.0
