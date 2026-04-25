"""End-to-end engine test for Mantle Cell Lymphoma — fitness-based + TP53 algorithm."""

from __future__ import annotations

import json
from pathlib import Path

from knowledge_base.engine import generate_plan, render_plan_html

REPO_ROOT = Path(__file__).parent.parent
KB_ROOT = REPO_ROOT / "knowledge_base" / "hosted" / "content"
EXAMPLES = REPO_ROOT / "examples"


def _patient(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_mcl_resolves():
    plan = generate_plan(_patient("patient_mcl_fit_younger.json"), kb_root=KB_ROOT)
    assert plan.disease_id == "DIS-MCL"
    assert plan.algorithm_id == "ALGO-MCL-1L"


def test_mcl_two_tracks():
    for name in ("patient_mcl_fit_younger.json", "patient_mcl_unfit_or_tp53.json"):
        plan = generate_plan(_patient(name), kb_root=KB_ROOT)
        track_ids = {t.track_id for t in plan.plan.tracks}
        assert track_ids == {"standard", "aggressive"}


def test_fit_younger_goes_intensive():
    plan = generate_plan(_patient("patient_mcl_fit_younger.json"), kb_root=KB_ROOT)
    assert plan.default_indication_id == "IND-MCL-1L-INTENSIVE"


def test_tp53_mutant_goes_btki_even_if_fit():
    plan = generate_plan(_patient("patient_mcl_unfit_or_tp53.json"), kb_root=KB_ROOT)
    assert plan.default_indication_id == "IND-MCL-1L-BTKI-R"


def test_intensive_regimen_uses_alternating_chop_dhap():
    plan = generate_plan(_patient("patient_mcl_fit_younger.json"), kb_root=KB_ROOT)
    aggressive = next(t for t in plan.plan.tracks if t.track_id == "aggressive")
    assert aggressive.regimen_data["id"] == "REG-MCL-INTENSIVE-RDHAP-AUTOSCT"
    drug_ids = {c["drug_id"] for c in aggressive.regimen_data["components"]}
    # R-CHOP backbone + DHAP additions
    assert {"DRUG-RITUXIMAB", "DRUG-CYCLOPHOSPHAMIDE", "DRUG-DOXORUBICIN",
            "DRUG-VINCRISTINE", "DRUG-PREDNISONE", "DRUG-DEXAMETHASONE",
            "DRUG-CYTARABINE"} <= drug_ids


def test_btki_regimen_uses_acalabrutinib_plus_rituximab():
    plan = generate_plan(_patient("patient_mcl_unfit_or_tp53.json"), kb_root=KB_ROOT)
    standard = next(t for t in plan.plan.tracks if t.track_id == "standard")
    assert standard.regimen_data["id"] == "REG-ACALABRUTINIB-RITUXIMAB"


def test_mcl_render_well_formed():
    plan = generate_plan(_patient("patient_mcl_fit_younger.json"), kb_root=KB_ROOT)
    html = render_plan_html(plan, mdt=None)
    assert "IND-MCL-1L-INTENSIVE" in html
    assert "IND-MCL-1L-BTKI-R" in html
