"""Tests for patient plan persistence (knowledge_base/engine/persistence.py).

Verifies:
1. save_result() writes to patient_plans/<patient_id>/<plan_id>.json
2. Round-trip: save → load reconstructs the same plan
3. Both PlanResult and DiagnosticPlanResult supported
4. list_versions() returns all versions sorted by mode + version
5. update_superseded_by_on_disk() mutates in place
6. revise_plan() + persistence integration: full chain saved both
   directions on disk
7. patient_id required (refuses to silently write to ANONYMOUS)

All tests use tmp_path fixture so they don't write to the real
patient_plans/ directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge_base.engine import (
    generate_diagnostic_brief,
    generate_plan,
    list_versions,
    load_result,
    revise_plan,
    save_result,
    update_superseded_by_on_disk,
)
from knowledge_base.engine.persistence import latest_version_path

REPO_ROOT = Path(__file__).parent.parent
KB_ROOT = REPO_ROOT / "knowledge_base" / "hosted" / "content"
EXAMPLES = REPO_ROOT / "examples"


def _patient(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


# ── Round-trip ────────────────────────────────────────────────────────────


def test_save_load_round_trip_treatment_plan(tmp_path):
    p = _patient("patient_zero_indolent.json")
    result = generate_plan(p, kb_root=KB_ROOT)
    saved_path = save_result(result, root=tmp_path)

    assert saved_path.exists()
    expected = tmp_path / "PZ-001-INDOLENT" / "PLAN-PZ-001-INDOLENT-V1.json"
    assert saved_path == expected

    loaded = load_result(saved_path)
    assert loaded.patient_id == result.patient_id
    assert loaded.plan.id == result.plan.id
    assert loaded.plan.version == result.plan.version
    assert loaded.default_indication_id == result.default_indication_id


def test_save_load_round_trip_diagnostic_plan(tmp_path):
    p = _patient("patient_diagnostic_lymphoma_suspect.json")
    result = generate_diagnostic_brief(p, kb_root=KB_ROOT)
    saved = save_result(result, root=tmp_path)

    expected = tmp_path / "PZ-DIAG-001" / "DPLAN-PZ-DIAG-001-V1.json"
    assert saved == expected

    loaded = load_result(saved)
    assert loaded.patient_id == result.patient_id
    assert loaded.diagnostic_plan.id == result.diagnostic_plan.id
    assert loaded.matched_workup_id == "WORKUP-SUSPECTED-LYMPHOMA"


def test_load_by_plan_id(tmp_path):
    """load_result accepts a plan_id and resolves via root glob."""
    p = _patient("patient_zero_indolent.json")
    result = generate_plan(p, kb_root=KB_ROOT)
    save_result(result, root=tmp_path)

    loaded = load_result("PLAN-PZ-001-INDOLENT-V1", root=tmp_path)
    assert loaded.plan.id == "PLAN-PZ-001-INDOLENT-V1"


# ── list_versions ─────────────────────────────────────────────────────────


def test_list_versions_empty(tmp_path):
    assert list_versions("PZ-NONEXISTENT", root=tmp_path) == []


def test_list_versions_sorts_diagnostic_first_then_by_version(tmp_path):
    susp = _patient("patient_diagnostic_lymphoma_suspect.json")
    confirmed = _patient("patient_diagnostic_lymphoma_confirmed.json")

    diag_v1 = generate_diagnostic_brief(susp, kb_root=KB_ROOT)
    save_result(diag_v1, root=tmp_path)

    _, plan_v1 = revise_plan(
        confirmed, diag_v1, "biopsy 2026-05-10: HCV-MZL confirmed",
        kb_root=KB_ROOT,
    )
    save_result(plan_v1, root=tmp_path)

    listed = list_versions("PZ-DIAG-001", root=tmp_path)
    assert len(listed) == 2
    assert listed[0]["mode"] == "diagnostic"
    assert listed[0]["plan_id"] == "DPLAN-PZ-DIAG-001-V1"
    assert listed[1]["mode"] == "treatment"
    assert listed[1]["plan_id"] == "PLAN-PZ-DIAG-001-V1"
    assert listed[1]["supersedes"] == "DPLAN-PZ-DIAG-001-V1"


# ── update_superseded_by_on_disk ──────────────────────────────────────────


def test_update_superseded_by_on_disk_treatment(tmp_path):
    p = _patient("patient_zero_indolent.json")
    result = generate_plan(p, kb_root=KB_ROOT)
    save_result(result, root=tmp_path)

    update_superseded_by_on_disk(
        "PLAN-PZ-001-INDOLENT-V1", "PLAN-PZ-001-INDOLENT-V2", root=tmp_path,
    )

    reloaded = load_result("PLAN-PZ-001-INDOLENT-V1", root=tmp_path)
    assert reloaded.plan.superseded_by == "PLAN-PZ-001-INDOLENT-V2"


def test_update_superseded_by_on_disk_diagnostic(tmp_path):
    p = _patient("patient_diagnostic_lymphoma_suspect.json")
    result = generate_diagnostic_brief(p, kb_root=KB_ROOT)
    save_result(result, root=tmp_path)

    update_superseded_by_on_disk(
        "DPLAN-PZ-DIAG-001-V1", "PLAN-PZ-DIAG-001-V1", root=tmp_path,
    )

    reloaded = load_result("DPLAN-PZ-DIAG-001-V1", root=tmp_path)
    assert reloaded.diagnostic_plan.superseded_by == "PLAN-PZ-DIAG-001-V1"


def test_update_superseded_by_missing_plan_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        update_superseded_by_on_disk("PLAN-NONEXISTENT", "PLAN-X", root=tmp_path)


# ── End-to-end: revise + persist closes the chain on disk ────────────────


def test_revise_then_save_keeps_chain_consistent_on_disk(tmp_path):
    """Real-world flow: save initial plan, regenerate after new data,
    save new + update old's superseded_by. Both files reflect the chain."""

    p_v1 = _patient("patient_zero_indolent.json")
    p_v2 = _patient("patient_zero_indolent_v2.json")

    plan_v1 = generate_plan(p_v1, kb_root=KB_ROOT)
    save_result(plan_v1, root=tmp_path)

    revised_prev, plan_v2 = revise_plan(
        p_v2, plan_v1, "lab update 2026-05-10", kb_root=KB_ROOT,
    )
    save_result(plan_v2, root=tmp_path)
    update_superseded_by_on_disk(
        plan_v1.plan.id, plan_v2.plan.id, root=tmp_path,
    )

    # Reload both — chain wired both directions
    reloaded_v1 = load_result(plan_v1.plan.id, root=tmp_path)
    reloaded_v2 = load_result(plan_v2.plan.id, root=tmp_path)
    assert reloaded_v1.plan.superseded_by == plan_v2.plan.id
    assert reloaded_v2.plan.supersedes == plan_v1.plan.id

    listed = list_versions(plan_v1.patient_id, root=tmp_path)
    assert len(listed) == 2
    assert listed[0]["plan_id"] == plan_v1.plan.id
    assert listed[1]["plan_id"] == plan_v2.plan.id
    assert listed[0]["superseded_by"] == plan_v2.plan.id
    assert listed[1]["supersedes"] == plan_v1.plan.id


# ── Guards ────────────────────────────────────────────────────────────────


def test_save_refuses_anonymous_patient(tmp_path):
    """patient_id is required for persistence path."""
    p = _patient("patient_zero_indolent.json")
    result = generate_plan(p, kb_root=KB_ROOT)
    result.patient_id = None  # synthetic anonymisation

    with pytest.raises(ValueError, match="patient_id"):
        save_result(result, root=tmp_path)


def test_latest_version_path_returns_most_recent(tmp_path):
    p = _patient("patient_zero_indolent.json")
    result = generate_plan(p, kb_root=KB_ROOT)
    save_result(result, root=tmp_path)
    assert latest_version_path(p["patient_id"], root=tmp_path) is not None
    assert latest_version_path("PZ-NONE", root=tmp_path) is None
