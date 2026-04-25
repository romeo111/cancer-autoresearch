"""Tests for the diagnostic-phase engine + MDT integration.

See specs/DIAGNOSTIC_MDT_SPEC.md. Verifies five contract properties:

1. Mode auto-detection: suspicion-only profile → diagnostic mode.
2. Hard rule (CHARTER §15.2 C7): generate_diagnostic_brief() refuses
   profiles with confirmed diagnosis.
3. Workup matching produces a populated DiagnosticPlan with workup
   steps (labs, imaging, histology) + mandatory questions.
4. orchestrate_mdt() in diagnostic mode produces hematologist /
   pathologist / radiologist required, infectious_disease_hepatology
   recommended (HCV/HBV unknown), and DQ-* open questions.
5. The diagnostic banner is non-empty (UI guard against automation
   bias per CHARTER §15.2 C6 + §15.2 C7).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge_base.engine import (
    generate_diagnostic_brief,
    is_diagnostic_profile,
    is_treatment_profile,
    orchestrate_mdt,
)
from knowledge_base.engine.diagnostic import _DIAGNOSTIC_BANNER

REPO_ROOT = Path(__file__).parent.parent
KB_ROOT = REPO_ROOT / "knowledge_base" / "hosted" / "content"
EXAMPLES = REPO_ROOT / "examples"


def _patient(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_mode_detection_suspicion_only():
    p = _patient("patient_diagnostic_lymphoma_suspect.json")
    assert is_diagnostic_profile(p) is True
    assert is_treatment_profile(p) is False


def test_mode_detection_treatment_profile():
    p = _patient("patient_zero_indolent.json")
    assert is_treatment_profile(p) is True
    # Has icd_o_3_morphology, no suspicion → not diagnostic
    assert is_diagnostic_profile(p) is False


def test_diagnostic_brief_blocks_confirmed_diagnosis():
    """CHARTER §15.2 C7 — the hard gate."""
    p = _patient("patient_zero_indolent.json")
    with pytest.raises(ValueError, match="confirmed diagnosis"):
        generate_diagnostic_brief(p, kb_root=KB_ROOT)


def test_diagnostic_brief_produces_populated_plan():
    p = _patient("patient_diagnostic_lymphoma_suspect.json")
    result = generate_diagnostic_brief(p, kb_root=KB_ROOT)

    assert result.diagnostic_plan is not None
    assert result.matched_workup_id == "WORKUP-SUSPECTED-LYMPHOMA"
    dp = result.diagnostic_plan
    assert dp.mode == "diagnostic"
    assert dp.id.startswith("DPLAN-PZ-DIAG-001")
    assert dp.workup_steps, "Workup must yield at least one step"
    # Histology step always last for any biopsy-driven workup
    assert dp.workup_steps[-1].category == "histology"
    assert dp.mandatory_questions, "Workup must surface at least one mandatory question"
    assert dp.expected_timeline_days is not None
    # Must NOT smuggle a treatment Plan in here
    assert not hasattr(dp, "tracks") or getattr(dp, "tracks", None) is None or getattr(dp, "tracks", []) == []


def test_diagnostic_mdt_brief_required_roles():
    p = _patient("patient_diagnostic_lymphoma_suspect.json")
    diag = generate_diagnostic_brief(p, kb_root=KB_ROOT)
    mdt = orchestrate_mdt(p, diag, kb_root=KB_ROOT)

    required = {r.role_id for r in mdt.required_roles}
    recommended = {r.role_id for r in mdt.recommended_roles}

    # D1: lymphoma suspicion → hematologist required
    assert "hematologist" in required
    # D2: any suspicion → pathologist required
    assert "pathologist" in required
    # D3: tissue_locations + splenic_mass_cm in findings → radiologist required
    assert "radiologist" in required
    # D5: HCV/HBV status unknown → infectious disease recommended
    assert "infectious_disease_hepatology" in recommended

    # Diagnostic-mode roles that should NOT fire (no regimen yet)
    not_expected_at_recommended_or_above = (
        {r.role_id for r in mdt.required_roles}
        | {r.role_id for r in mdt.recommended_roles}
    )
    assert "clinical_pharmacist" not in not_expected_at_recommended_or_above, (
        "diagnostic mode must NOT recommend clinical_pharmacist — there is no regimen yet"
    )


def test_diagnostic_mdt_open_questions():
    p = _patient("patient_diagnostic_lymphoma_suspect.json")
    diag = generate_diagnostic_brief(p, kb_root=KB_ROOT)
    mdt = orchestrate_mdt(p, diag, kb_root=KB_ROOT)

    qids = {q.id for q in mdt.open_questions}
    # DQ1, DQ2, DQ3 all blocking for this profile
    assert "DQ-CD20-AFTER-BIOPSY" in qids
    assert "DQ-HBV-SEROLOGY-EARLY" in qids
    assert "DQ-STAGING-PLAN" in qids
    # DQ4 — multiple working_hypotheses present
    assert "DQ-DIFFERENTIAL" in qids

    blocking_count = sum(1 for q in mdt.open_questions if q.blocking)
    assert blocking_count >= 3


def test_diagnostic_mdt_aggregation_summary_marks_mode():
    p = _patient("patient_diagnostic_lymphoma_suspect.json")
    diag = generate_diagnostic_brief(p, kb_root=KB_ROOT)
    mdt = orchestrate_mdt(p, diag, kb_root=KB_ROOT)
    agg = mdt.aggregation_summary
    assert agg.get("mode") == "diagnostic"
    assert agg.get("matched_workup_id") == "WORKUP-SUSPECTED-LYMPHOMA"
    assert agg.get("workup_steps", 0) >= 4


def test_diagnostic_banner_non_empty():
    assert "DIAGNOSTIC PHASE" in _DIAGNOSTIC_BANNER
    assert "Histology required" in _DIAGNOSTIC_BANNER


def test_diagnostic_brief_warns_when_no_workup_matches():
    """Profile with suspicion that no DiagnosticWorkup matches —
    result returned with explicit warning, no exception."""
    p = {
        "patient_id": "PZ-DIAG-NOMATCH",
        "disease": {
            "suspicion": {
                "lineage_hint": "exotic_disease_unknown_to_kb",
                "tissue_locations": ["nowhere_specific"],
                "presentation": "totally unrelated symptoms",
            }
        },
    }
    result = generate_diagnostic_brief(p, kb_root=KB_ROOT)
    assert result.diagnostic_plan is None
    assert any("No DiagnosticWorkup matched" in w for w in result.warnings)


def test_treatment_mode_mdt_still_works_after_diagnostic_addition():
    """Regression: making MDT orchestrator polymorphic must not break
    existing treatment-mode behaviour."""
    p = _patient("patient_zero_indolent.json")
    from knowledge_base.engine import generate_plan

    plan_result = generate_plan(p, kb_root=KB_ROOT)
    mdt = orchestrate_mdt(p, plan_result, kb_root=KB_ROOT)
    assert mdt.disease_id == "DIS-HCV-MZL"
    # Treatment-mode tag (no `mode` key) — confirms we ran the treatment branch
    assert mdt.aggregation_summary.get("mode") != "diagnostic"
