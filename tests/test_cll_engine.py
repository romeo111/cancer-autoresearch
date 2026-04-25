"""End-to-end engine test for CLL/SLL — modern era (BTKi vs VenO)."""

from __future__ import annotations

import json
from pathlib import Path

from knowledge_base.engine import generate_plan, render_plan_html

REPO_ROOT = Path(__file__).parent.parent
KB_ROOT = REPO_ROOT / "knowledge_base" / "hosted" / "content"
EXAMPLES = REPO_ROOT / "examples"


def _patient(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_cll_resolves_via_icd_o_3():
    plan = generate_plan(_patient("patient_cll_low_risk.json"), kb_root=KB_ROOT)
    assert plan.disease_id == "DIS-CLL"
    assert plan.algorithm_id == "ALGO-CLL-1L"


def test_cll_two_tracks():
    for name in ("patient_cll_low_risk.json", "patient_cll_high_risk.json"):
        plan = generate_plan(_patient(name), kb_root=KB_ROOT)
        track_ids = {t.track_id for t in plan.plan.tracks}
        assert track_ids == {"standard", "aggressive"}


def test_low_risk_defaults_to_btki():
    plan = generate_plan(_patient("patient_cll_low_risk.json"), kb_root=KB_ROOT)
    assert plan.default_indication_id == "IND-CLL-1L-BTKI"


def test_high_risk_defaults_to_veno():
    plan = generate_plan(_patient("patient_cll_high_risk.json"), kb_root=KB_ROOT)
    assert plan.default_indication_id == "IND-CLL-1L-VENO"


def test_high_risk_redflag_in_trace():
    plan = generate_plan(_patient("patient_cll_high_risk.json"), kb_root=KB_ROOT)
    assert "RF-CLL-HIGH-RISK" in json.dumps(plan.trace)


def test_btki_track_uses_acalabrutinib():
    plan = generate_plan(_patient("patient_cll_low_risk.json"), kb_root=KB_ROOT)
    standard = next(t for t in plan.plan.tracks if t.track_id == "standard")
    assert standard.regimen_data["id"] == "REG-ACALABRUTINIB-CONTINUOUS"
    drug_ids = {c["drug_id"] for c in standard.regimen_data["components"]}
    assert "DRUG-ACALABRUTINIB" in drug_ids


def test_veno_track_uses_venetoclax_obinutuzumab():
    plan = generate_plan(_patient("patient_cll_high_risk.json"), kb_root=KB_ROOT)
    aggressive = next(t for t in plan.plan.tracks if t.track_id == "aggressive")
    assert aggressive.regimen_data["id"] == "REG-VENETOCLAX-OBINUTUZUMAB"
    drug_ids = {c["drug_id"] for c in aggressive.regimen_data["components"]}
    assert "DRUG-VENETOCLAX" in drug_ids
    assert "DRUG-OBINUTUZUMAB" in drug_ids
    assert "DRUG-ALLOPURINOL" in drug_ids  # TLS prophylaxis embedded


def test_cll_render_well_formed():
    p = _patient("patient_cll_high_risk.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    html = render_plan_html(plan, mdt=None)
    assert "IND-CLL-1L-BTKI" in html
    assert "IND-CLL-1L-VENO" in html
