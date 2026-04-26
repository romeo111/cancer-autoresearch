"""Tests for Phase B writers (state + audit log + metrics CSV).

Plan: docs/plans/scheduled_kb_audit_2026-04-26.md §2.4 + §5 + §7.2.
Module: scripts/audit_writers.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest


def _import_writers():
    import sys
    REPO_ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(REPO_ROOT))
    import scripts.audit_writers as writers  # noqa: E402
    return writers


def _sample_plan(**overrides) -> dict:
    """Minimal action_plan dict matching the orchestrator's schema."""
    base = {
        "run_id": "audit-2026-04-26-monthly",
        "started_at": "2026-04-26T09:00:00+00:00",
        "git_sha": "abc123def456",
        "today": "2026-04-26",
        "snapshot": {
            "biomarkers": {
                "defined": 62, "referenced": 62, "dormant_count": 0,
                "missing_count": 0, "naming_mismatch_count": 0,
                "loinc_missing_count": 57,
                "missing_ids": [], "dormant_ids": [], "naming_pairs": [],
            },
            "validator": {
                "loaded_entities": 1245, "schema_errors_count": 0,
                "ref_errors_count": 0,
            },
            "freshness": {"total_breaches": 14, "by_entity_type": {
                "Drug": {"stale_past_sla": 0, "never_reviewed": 5, "fresh": 45},
                "Indication": {"stale_past_sla": 2, "never_reviewed": 7, "fresh": 50},
            }},
        },
        "deltas": [
            {"kind": "missing_ref", "key": "BIO-FOO"},
        ],
        "actions": [
            {
                "type": "open_issue",
                "dedupe_key": "kb-audit-key-v1:missing_ref:BIO-FOO",
                "title": "[kb-audit] BIO-FOO referenced but no entity file",
                "labels": ["kb-audit", "blocker"],
                "body": "...",
                "rationale": "new broken ref",
            },
        ],
        "diagnostics": {
            "deltas_detected": 1, "actions_taken": 1,
            "actions_suppressed_idempotency": 0, "actions_capped": 0,
            "preflight_aborted": False, "abort_reason": None,
        },
    }
    base.update(overrides)
    return base


# ── State file ──────────────────────────────────────────────────────────


def test_state_file_round_trips_through_json(tmp_path):
    writers = _import_writers()
    plan = _sample_plan()
    state_path = tmp_path / "state.json"
    writers.write_state_file(plan, state_path, previous_open_issues={})

    loaded = json.loads(state_path.read_text(encoding="utf-8"))
    assert loaded["biomarkers"]["defined"] == 62
    assert loaded["validator"]["schema_errors_count"] == 0
    assert loaded["freshness"]["total_breaches"] == 14
    assert loaded["last_run_id"] == plan["run_id"]


def test_open_issue_action_adds_to_open_issues_map():
    writers = _import_writers()
    plan = _sample_plan()
    payload = writers.build_state_payload(plan, previous_open_issues={})
    key = "kb-audit-key-v1:missing_ref:BIO-FOO"
    assert key in payload["open_issues"]
    # In dry-run we record None placeholder; Phase C executors patch
    # with real numbers after gh-CLI succeeds.
    assert payload["open_issues"][key] is None


def test_close_issue_action_removes_from_open_map():
    writers = _import_writers()
    plan = _sample_plan(actions=[{
        "type": "close_issue",
        "dedupe_key": "kb-audit-key-v1:dormant_appeared:BIO-OLD",
        "issue_number": 42,
        "body": "resolved",
        "rationale": "test",
    }])
    payload = writers.build_state_payload(
        plan,
        previous_open_issues={
            "kb-audit-key-v1:dormant_appeared:BIO-OLD": 42,
            "kb-audit-key-v1:dormant_appeared:BIO-OTHER": 99,
        },
    )
    assert "kb-audit-key-v1:dormant_appeared:BIO-OLD" not in payload["open_issues"]
    assert "kb-audit-key-v1:dormant_appeared:BIO-OTHER" in payload["open_issues"]


def test_comment_issue_keeps_existing_entry():
    writers = _import_writers()
    plan = _sample_plan(actions=[{
        "type": "comment_issue",
        "dedupe_key": "kb-audit-key-v1:freshness_breach:Drug",
        "issue_number": 7,
        "body": "still seen",
        "rationale": "refresh",
    }])
    payload = writers.build_state_payload(
        plan,
        previous_open_issues={"kb-audit-key-v1:freshness_breach:Drug": 7},
    )
    assert payload["open_issues"]["kb-audit-key-v1:freshness_breach:Drug"] == 7


def test_unknown_action_types_dont_corrupt_open_map():
    writers = _import_writers()
    plan = _sample_plan(actions=[
        {"type": "no_op", "dedupe_key": "x", "rationale": "noop"},
        {"type": "commit_catalog_refresh", "dedupe_key": "catalog-refresh",
         "files": [], "message": "chore(catalog): test", "rationale": "x"},
    ])
    payload = writers.build_state_payload(
        plan, previous_open_issues={"existing": 1},
    )
    # Unrelated map entries preserved
    assert payload["open_issues"]["existing"] == 1
    # Catalog refresh / no_op don't add or remove keys
    assert "catalog-refresh" not in payload["open_issues"]
    assert "x" not in payload["open_issues"]


# ── Audit log markdown ──────────────────────────────────────────────────


def test_audit_log_md_contains_required_sections():
    writers = _import_writers()
    md = writers.render_audit_log_md(_sample_plan())
    assert "# KB audit" in md
    assert "## Snapshot" in md
    assert "## Deltas detected" in md
    assert "## Actions" in md
    assert "## Diagnostics" in md


def test_audit_log_md_surfaces_action_titles():
    writers = _import_writers()
    md = writers.render_audit_log_md(_sample_plan())
    assert "BIO-FOO referenced but no entity file" in md


def test_audit_log_md_handles_aborted_plan():
    writers = _import_writers()
    plan = _sample_plan(diagnostics={
        "preflight_aborted": True, "abort_reason": "git not clean",
        "deltas_detected": 0, "actions_taken": 0,
        "actions_suppressed_idempotency": 0, "actions_capped": 0,
    })
    md = writers.render_audit_log_md(plan)
    assert "❌ ABORTED" in md
    assert "git not clean" in md
    # Should NOT have a snapshot table (we aborted before collecting)
    assert "## Snapshot" not in md


def test_audit_log_filename_collision_gets_suffix(tmp_path):
    writers = _import_writers()
    plan = _sample_plan()
    p1 = writers.write_audit_log(plan, tmp_path)
    p2 = writers.write_audit_log(plan, tmp_path)
    p3 = writers.write_audit_log(plan, tmp_path)
    assert p1.name == "2026-04-26.md"
    assert p2.name == "2026-04-26-2.md"
    assert p3.name == "2026-04-26-3.md"


# ── Metrics CSV ─────────────────────────────────────────────────────────


def test_metrics_csv_writes_header_on_first_run(tmp_path):
    writers = _import_writers()
    csv_path = tmp_path / "metrics.csv"
    writers.append_metrics_csv(_sample_plan(), csv_path)
    text = csv_path.read_text(encoding="utf-8")
    # Header line uses comma-separated column names
    assert "date,run_id,git_sha" in text
    assert "biomarkers_defined" in text
    assert "freshness_breaches" in text


def test_metrics_csv_appends_without_duplicate_header(tmp_path):
    writers = _import_writers()
    csv_path = tmp_path / "metrics.csv"
    writers.append_metrics_csv(_sample_plan(), csv_path)
    writers.append_metrics_csv(_sample_plan(today="2026-05-01",
                                            run_id="audit-2026-05-01-monthly"),
                               csv_path)
    text = csv_path.read_text(encoding="utf-8")
    # Header should appear exactly once
    assert text.count("date,run_id,git_sha") == 1


def test_metrics_csv_row_columns_match_spec(tmp_path):
    writers = _import_writers()
    csv_path = tmp_path / "metrics.csv"
    writers.append_metrics_csv(_sample_plan(), csv_path)
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    row = rows[0]
    # Check all spec'd columns present
    for col in writers.METRICS_CSV_COLUMNS:
        assert col in row, f"missing column {col}"
    assert row["biomarkers_defined"] == "62"
    assert row["schema_errors"] == "0"


# ── Combined persist ────────────────────────────────────────────────────


def test_persist_plan_outputs_writes_all_three(tmp_path):
    writers = _import_writers()
    audit_dir = tmp_path / "audit_log"
    state_file = tmp_path / ".state.json"
    metrics_csv = tmp_path / "metrics.csv"

    written = writers.persist_plan_outputs(
        _sample_plan(),
        audit_log_dir=audit_dir,
        state_file=state_file,
        metrics_csv=metrics_csv,
        previous_open_issues={},
    )

    assert written["audit_log"].is_file()
    assert state_file.is_file()
    assert metrics_csv.is_file()


def test_state_file_atomic_write_preserves_old_on_failure(tmp_path, monkeypatch):
    """If the tmpfile rename fails, the old state file must remain.
    write_state_file writes to .tmp first, then renames atomically."""
    writers = _import_writers()
    state_file = tmp_path / "state.json"
    state_file.write_text('{"existing": "state"}', encoding="utf-8")

    # Simulate atomic rename failure mid-write
    original_replace = Path.replace
    def fake_replace(self, target):
        raise OSError("disk full")
    monkeypatch.setattr(Path, "replace", fake_replace)

    with pytest.raises(OSError):
        writers.write_state_file(_sample_plan(), state_file,
                                 previous_open_issues={})

    # Old content preserved
    assert state_file.read_text(encoding="utf-8") == '{"existing": "state"}'
