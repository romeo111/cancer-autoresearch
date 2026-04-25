"""End-to-end tests for the rule engine on the HCV-MZL reference case."""

from __future__ import annotations

import json
from pathlib import Path

from knowledge_base.engine import generate_plan

REPO_ROOT = Path(__file__).parent.parent
KB_ROOT = REPO_ROOT / "knowledge_base" / "hosted" / "content"
EXAMPLES = REPO_ROOT / "examples"


def _patient(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_indolent_hcv_mzl_picks_antiviral_default():
    """Low-burden HCV-MZL patient: antiviral-only should be the default,
    BR should be the alternative."""

    result = generate_plan(_patient("patient_zero_indolent.json"), kb_root=KB_ROOT)

    assert result.disease_id == "DIS-HCV-MZL"
    assert result.algorithm_id == "ALGO-HCV-MZL-1L"
    assert result.default_indication_id == "IND-HCV-MZL-1L-ANTIVIRAL"
    assert result.alternative_indication_id == "IND-HCV-MZL-1L-BR-AGGRESSIVE"
    assert result.warnings == []


def test_bulky_hcv_mzl_picks_br_default():
    """Bulky HCV-MZL patient: BR should become the default via
    RF-BULKY-DISEASE firing; antiviral remains the alternative."""

    result = generate_plan(_patient("patient_zero_bulky.json"), kb_root=KB_ROOT)

    assert result.disease_id == "DIS-HCV-MZL"
    assert result.default_indication_id == "IND-HCV-MZL-1L-BR-AGGRESSIVE"
    assert result.alternative_indication_id == "IND-HCV-MZL-1L-ANTIVIRAL"
    # RF-BULKY-DISEASE fired at step 1
    step_1 = next((t for t in result.trace if t.get("step") == 1), None)
    assert step_1 is not None
    assert step_1["outcome"] is True


def test_plan_result_has_full_indication_records():
    """PlanResult should carry fully-materialised Indication data for rendering."""

    result = generate_plan(_patient("patient_zero_indolent.json"), kb_root=KB_ROOT)
    assert result.default_indication is not None
    assert result.default_indication.get("id") == "IND-HCV-MZL-1L-ANTIVIRAL"
    assert result.default_indication.get("recommended_regimen") == "REG-DAA-SOF-VEL"


def test_plan_object_has_two_tracks_in_one_document():
    """Per CHARTER §2 the Plan presents both alternatives in one document
    (one Plan, multiple PlanTrack entries). One track is marked is_default."""

    result = generate_plan(_patient("patient_zero_indolent.json"), kb_root=KB_ROOT)
    assert result.plan is not None
    assert len(result.plan.tracks) >= 2
    defaults = [t for t in result.plan.tracks if t.is_default]
    assert len(defaults) == 1, "exactly one track should be marked as engine default"
    assert defaults[0].indication_id == "IND-HCV-MZL-1L-ANTIVIRAL"


def test_plan_carries_fda_compliance_metadata():
    """Per CHARTER §15 every Plan must surface the FDA Criterion-4 elements
    so an HCP can independently review the basis."""

    result = generate_plan(_patient("patient_zero_indolent.json"), kb_root=KB_ROOT)
    fda = result.plan.fda_compliance
    assert fda.intended_use
    assert fda.hcp_user_specification
    assert fda.patient_population_match
    assert fda.algorithm_summary
    assert fda.automation_bias_warning
    assert fda.time_critical is False  # outpatient cancer planning
    assert fda.data_sources_summary, "Plan must cite at least one source"


def test_plan_tracks_materialize_regimen_and_supportive_care():
    """Aggressive (BR) track should bring its full Regimen + supportive care
    references into the Plan output for one-document rendering."""

    result = generate_plan(_patient("patient_zero_bulky.json"), kb_root=KB_ROOT)
    default = next(t for t in result.plan.tracks if t.is_default)
    assert default.indication_id == "IND-HCV-MZL-1L-BR-AGGRESSIVE"
    assert default.regimen_data is not None
    assert default.regimen_data.get("id") == "REG-BR-STANDARD"
    # BR has mandatory supportive care wired (antiemetic + PJP)
    assert len(default.supportive_care_data) >= 2
    # And hard contraindications are surfaced
    assert len(default.contraindications_data) >= 1
