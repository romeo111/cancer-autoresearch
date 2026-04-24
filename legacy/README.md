# Legacy — pre-OpenOnco autoresearch pipeline

This directory holds the original Cancer AutoResearch code and data. It
produced the research reports behind the project's first real-patient
treatment plans, which clinicians judged "pretty strong" on 2026-04-24.

## Why it's archived, not deleted

- `experiment_reports/` are the artifacts that fed the first-patient
  deliverables — the signal source for the positive clinician review.
- `loop/strategy.md` captures the research strategy that produced those
  reports. OpenOnco's rule engine has to produce at least as comprehensive
  an output, so this is the calibration target.
- Nothing here is broken. It is being retired because the approach
  (LLM ranks treatments 1–10) conflicts with `CHARTER.md` §8.3
  (forbidden prompt patterns).

## Layout

| Path | Contents |
|---|---|
| `skill/` | Claude Skill definition, JSON output template |
| `loop/` | Karpathy-style autoresearch loop (`auto_loop`, `strategy`, `program`, `strategy_optimizer`, `run_experiment`, `generate_cases`) |
| `scoring/` | 0–100 rubric scorer (`evaluate`, `cancer_research_scorer`) |
| `virtual_board/` | 5-doctor adversarial review module |
| `storage/` | Old SQLite DB + filesystem DB + query API (`research_db.py`, `database_api.py`, `research_db/`) |
| `distributed/` | HTTP orchestrator + workers (`server.py`, `worker.py`) |
| `local_gpu/` | Abandoned RTX 5050 fine-tune pipeline + ~33 MB training data |
| `benchmark_cases/` | Original HN / lung / tongue-neck benchmark sets |
| `docs/` | Original project docs (`ARCHITECTURE`, `SCHEMA_REFERENCE`, etc.) |
| `experiment_reports/` | ~200 generated reports + 22 strategy variants |
| `tasks/` | ~100 re-eval prompts from local_task_generator |
| `finetune_data/` | ChatML/Alpaca training pairs (abandoned) |

## Known broken bits

- `.github/workflows/score_reports.yml` points at the old `evaluate.py`
  path and triggers on `experiment_reports/**/*_report.json`. With the
  reports now under `legacy/`, it no longer fires for new changes. Left
  as-is; OpenOnco will need its own CI (citation check + two-reviewer
  approval), not a rubric score.

## Not here

- Real patient deliverables (`*план лікування.html`) stay at repo root,
  gitignored per `CHARTER.md` §9.3 (informed consent + de-identification
  + ethics approval required before publication).
