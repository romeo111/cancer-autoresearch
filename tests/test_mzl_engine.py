"""End-to-end tests for splenic + nodal MZL — the 2 remaining MZL subtypes
joining HCV-MZL extranodal already in KB."""

from __future__ import annotations

import json
from pathlib import Path

from knowledge_base.engine import generate_plan

REPO_ROOT = Path(__file__).parent.parent
KB_ROOT = REPO_ROOT / "knowledge_base" / "hosted" / "content"
EXAMPLES = REPO_ROOT / "examples"


def _patient(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


# ── Splenic MZL ───────────────────────────────────────────────────────────


def test_smzl_disease_resolves():
    plan = generate_plan(_patient("patient_smzl_hcv_positive.json"), kb_root=KB_ROOT)
    assert plan.disease_id == "DIS-SPLENIC-MZL"
    assert plan.algorithm_id == "ALGO-SMZL-1L"


def test_smzl_hcv_positive_routes_to_daa():
    plan = generate_plan(_patient("patient_smzl_hcv_positive.json"), kb_root=KB_ROOT)
    assert plan.default_indication_id == "IND-SMZL-1L-HCV-POSITIVE"


def test_smzl_hcv_negative_routes_to_rituximab():
    plan = generate_plan(_patient("patient_smzl_hcv_negative.json"), kb_root=KB_ROOT)
    assert plan.default_indication_id == "IND-SMZL-1L-RITUXIMAB"


def test_smzl_hcv_positive_uses_shared_daa_regimen():
    """Cross-disease regimen reuse — same DAA regimen serves HCV-MZL
    extranodal and HCV-SMZL."""
    plan = generate_plan(_patient("patient_smzl_hcv_positive.json"), kb_root=KB_ROOT)
    standard = next(t for t in plan.plan.tracks if t.track_id == "standard")
    assert standard.regimen_data["id"] == "REG-DAA-SOF-VEL"


# ── Nodal MZL ─────────────────────────────────────────────────────────────


def test_nmzl_disease_resolves_via_id():
    plan = generate_plan(_patient("patient_nmzl_low_burden.json"), kb_root=KB_ROOT)
    assert plan.disease_id == "DIS-NODAL-MZL"
    assert plan.algorithm_id == "ALGO-NMZL-1L"


def test_nmzl_low_burden_defaults_to_watch():
    plan = generate_plan(_patient("patient_nmzl_low_burden.json"), kb_root=KB_ROOT)
    assert plan.default_indication_id == "IND-NMZL-1L-WATCH"


def test_nmzl_three_track_plan():
    """NMZL 1L has 3 tracks: surveillance + BR + R-CHOP-aggressive
    (sharing FL's aggressive indication)."""
    plan = generate_plan(_patient("patient_nmzl_low_burden.json"), kb_root=KB_ROOT)
    track_ids = {t.track_id for t in plan.plan.tracks}
    assert track_ids == {"surveillance", "standard", "aggressive"}
    # Aggressive shares with FL — verify the actual indication is FL's
    aggressive = next(t for t in plan.plan.tracks if t.track_id == "aggressive")
    assert aggressive.indication_id == "IND-FL-1L-RCHOP-AGGRESSIVE"
