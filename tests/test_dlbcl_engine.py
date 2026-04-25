"""End-to-end engine test for DLBCL NOS — Tier 1 first aggressive lymphoma.

Validates the IPI-driven decision: low-IPI → R-CHOP standard;
high-IPI (RF-DLBCL-HIGH-IPI fired) → Pola-R-CHP aggressive.
"""

from __future__ import annotations

import json
from pathlib import Path

from knowledge_base.engine import (
    generate_plan,
    orchestrate_mdt,
    render_plan_html,
)

REPO_ROOT = Path(__file__).parent.parent
KB_ROOT = REPO_ROOT / "knowledge_base" / "hosted" / "content"
EXAMPLES = REPO_ROOT / "examples"


def _patient(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


# ── Disease + algorithm resolution ────────────────────────────────────────


def test_dlbcl_disease_resolves_via_icd_o_3():
    p = _patient("patient_dlbcl_low_ipi.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    assert plan.disease_id == "DIS-DLBCL-NOS"
    assert plan.algorithm_id == "ALGO-DLBCL-1L"


def test_dlbcl_two_tracks_present():
    for name in ("patient_dlbcl_low_ipi.json", "patient_dlbcl_high_ipi.json"):
        p = _patient(name)
        plan = generate_plan(p, kb_root=KB_ROOT)
        assert plan.plan is not None, f"{name}: no Plan object"
        assert len(plan.plan.tracks) == 2
        track_ids = {t.track_id for t in plan.plan.tracks}
        assert track_ids == {"standard", "aggressive"}, (
            f"{name}: unexpected tracks {track_ids}"
        )


def test_low_ipi_patient_defaults_to_rchop():
    p = _patient("patient_dlbcl_low_ipi.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    assert plan.default_indication_id == "IND-DLBCL-1L-RCHOP"
    assert plan.alternative_indication_id == "IND-DLBCL-1L-POLA-R-CHP"


def test_high_ipi_patient_defaults_to_pola_r_chp():
    p = _patient("patient_dlbcl_high_ipi.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    assert plan.default_indication_id == "IND-DLBCL-1L-POLA-R-CHP"
    assert plan.alternative_indication_id == "IND-DLBCL-1L-RCHOP"


def test_high_ipi_redflag_appears_in_trace():
    p = _patient("patient_dlbcl_high_ipi.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    trace_str = json.dumps(plan.trace)
    assert "RF-DLBCL-HIGH-IPI" in trace_str, (
        f"high-IPI RedFlag not surfaced in trace: {plan.trace}"
    )


# ── Regimen materialization ───────────────────────────────────────────────


def test_rchop_track_carries_5_drug_regimen():
    p = _patient("patient_dlbcl_low_ipi.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    standard = next(t for t in plan.plan.tracks if t.track_id == "standard")
    reg = standard.regimen_data
    assert reg["id"] == "REG-R-CHOP"
    drug_ids = {c["drug_id"] for c in reg["components"]}
    assert drug_ids == {
        "DRUG-RITUXIMAB",
        "DRUG-CYCLOPHOSPHAMIDE",
        "DRUG-DOXORUBICIN",
        "DRUG-VINCRISTINE",
        "DRUG-PREDNISONE",
    }


def test_pola_r_chp_track_replaces_vincristine_with_polatuzumab():
    p = _patient("patient_dlbcl_high_ipi.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    aggressive = next(t for t in plan.plan.tracks if t.track_id == "aggressive")
    reg = aggressive.regimen_data
    assert reg["id"] == "REG-POLA-R-CHP"
    drug_ids = {c["drug_id"] for c in reg["components"]}
    # Pola-R-CHP: polatuzumab REPLACES vincristine
    assert "DRUG-POLATUZUMAB-VEDOTIN" in drug_ids
    assert "DRUG-VINCRISTINE" not in drug_ids
    # Other backbone preserved
    assert {"DRUG-RITUXIMAB", "DRUG-CYCLOPHOSPHAMIDE",
            "DRUG-DOXORUBICIN", "DRUG-PREDNISONE"} <= drug_ids


def test_dlbcl_hard_contraindications_surfaced():
    """Both tracks carry HBV-no-prophylaxis + LVEF-low; aggressive also
    flags severe-neuropathy CI from polatuzumab."""
    p = _patient("patient_dlbcl_low_ipi.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    standard = next(t for t in plan.plan.tracks if t.track_id == "standard")
    ci_ids = {c["id"] for c in standard.contraindications_data}
    assert {"CI-HBV-NO-PROPHYLAXIS", "CI-LVEF-LOW-FOR-ANTHRACYCLINE"} <= ci_ids

    aggressive = next(t for t in plan.plan.tracks if t.track_id == "aggressive")
    ci_ids_agg = {c["id"] for c in aggressive.contraindications_data}
    assert "CI-BORTEZOMIB-SEVERE-NEUROPATHY" in ci_ids_agg


def test_dlbcl_monitoring_schedule_attached():
    p = _patient("patient_dlbcl_low_ipi.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    standard = next(t for t in plan.plan.tracks if t.track_id == "standard")
    assert standard.monitoring_data is not None
    assert standard.monitoring_data["id"] == "MON-R-CHOP-REGIMEN"
    phase_names = {ph["name"] for ph in standard.monitoring_data["phases"]}
    assert "baseline" in phase_names
    assert "interim_response_assessment" in phase_names
    assert "end_of_treatment" in phase_names


# ── Render ────────────────────────────────────────────────────────────────


def test_dlbcl_html_render_well_formed_for_both_patients():
    for name in ("patient_dlbcl_low_ipi.json", "patient_dlbcl_high_ipi.json"):
        p = _patient(name)
        plan = generate_plan(p, kb_root=KB_ROOT)
        mdt = orchestrate_mdt(p, plan, kb_root=KB_ROOT)
        html = render_plan_html(plan, mdt=mdt)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
        assert "IND-DLBCL-1L-RCHOP" in html
        assert "IND-DLBCL-1L-POLA-R-CHP" in html
        assert "SRC-NCCN-BCELL-2025" in html
