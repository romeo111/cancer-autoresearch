"""Cross-disease TP53 biomarker wiring test.

BIO-TP53-MUTATION is the standalone marker entity that powers TP53-driven
decisions in CLL, MCL, MM (and future DLBCL/AML 2L). This test verifies:

1. The biomarker entity loads + has source citations from all three
   downstream NCCN guidelines.
2. Composite biomarkers (CLL high-risk, MM high-risk cytogenetics) cite
   it via related_biomarkers.
3. RedFlags (CLL high-risk, MCL blastoid/TP53) accept BIO-TP53-MUTATION
   as a trigger finding (so a clinician supplying just "TP53 positive"
   correctly fires the algorithm).
4. End-to-end: a CLL patient with only the TP53 finding (no composite
   pre-computed) still routes to VenO; a MCL patient with only TP53
   still routes to BTKi-R.
"""

from __future__ import annotations

import json
from pathlib import Path

from knowledge_base.engine import generate_plan
from knowledge_base.validation.loader import load_content

REPO_ROOT = Path(__file__).parent.parent
KB_ROOT = REPO_ROOT / "knowledge_base" / "hosted" / "content"


def _load() -> dict:
    return load_content(KB_ROOT).entities_by_id


def test_tp53_biomarker_entity_loads_with_three_disease_sources():
    """BIO-TP53-MUTATION must cite NCCN B-cell + NCCN MM + NCCN AML
    (cross-disease relevance baked into source list)."""
    ents = _load()
    assert "BIO-TP53-MUTATION" in ents
    bio = ents["BIO-TP53-MUTATION"]["data"]
    sources = set(bio.get("sources") or [])
    assert {"SRC-NCCN-BCELL-2025", "SRC-NCCN-MM-2025",
            "SRC-NCCN-AML-2025"} <= sources, (
        f"TP53 entity must cite all 3 downstream guidelines; got: {sources}"
    )
    # Mutation details specify gene + functional impact
    md = bio.get("mutation_details") or {}
    assert md.get("gene") == "TP53"
    assert "loss_of_function" in (md.get("functional_impact") or "").lower()


def test_composite_cll_cites_tp53_via_related():
    """BIO-CLL-HIGH-RISK-GENETICS related_biomarkers includes TP53."""
    ents = _load()
    cll_composite = ents["BIO-CLL-HIGH-RISK-GENETICS"]["data"]
    related = set(cll_composite.get("related_biomarkers") or [])
    assert "BIO-TP53-MUTATION" in related


def test_composite_mm_cites_tp53_via_related():
    """BIO-MM-CYTOGENETICS-HR related_biomarkers includes TP53 (del 17p
    is part of the high-risk MM cytogenetics composite)."""
    ents = _load()
    mm_composite = ents["BIO-MM-CYTOGENETICS-HR"]["data"]
    related = set(mm_composite.get("related_biomarkers") or [])
    assert "BIO-TP53-MUTATION" in related


def test_cll_redflag_accepts_tp53_as_direct_finding():
    """RF-CLL-HIGH-RISK trigger any_of must accept BIO-TP53-MUTATION
    as a standalone finding so the engine fires on minimal input."""
    ents = _load()
    rf = ents["RF-CLL-HIGH-RISK"]["data"]
    findings = {c.get("finding") for c in rf["trigger"]["any_of"]}
    assert "BIO-TP53-MUTATION" in findings


def test_mcl_redflag_accepts_tp53_as_direct_finding():
    """RF-MCL-BLASTOID-OR-TP53 trigger any_of must accept BIO-TP53-MUTATION
    so a TP53-only minimal patient profile still triggers the algorithm."""
    ents = _load()
    rf = ents["RF-MCL-BLASTOID-OR-TP53"]["data"]
    findings = {c.get("finding") for c in rf["trigger"]["any_of"]}
    assert "BIO-TP53-MUTATION" in findings


# ── End-to-end: minimal-input patients route correctly via TP53 entity ───


def test_cll_with_only_tp53_biomarker_routes_to_veno():
    """A CLL patient with ONLY BIO-TP53-MUTATION=positive (no composite
    or per-component findings pre-computed) should still route to VenO
    via the new direct-trigger wire."""
    patient = {
        "patient_id": "CLL-TP53-ONLY-001",
        "disease": {"icd_o_3_morphology": "9823/3"},
        "line_of_therapy": 1,
        "biomarkers": {"BIO-TP53-MUTATION": "positive"},
        "demographics": {"age": 65, "sex": "male", "ecog": 1},
        "findings": {"iwcll_treatment_indication": True},
    }
    plan = generate_plan(patient, kb_root=KB_ROOT)
    assert plan.disease_id == "DIS-CLL"
    assert plan.default_indication_id == "IND-CLL-1L-VENO"


def test_mcl_with_only_tp53_biomarker_routes_to_btki():
    """An MCL patient with ONLY BIO-TP53-MUTATION=positive should route
    to BTKi-R regardless of fitness — TP53 trumps fitness in MCL algo."""
    patient = {
        "patient_id": "MCL-TP53-ONLY-001",
        "disease": {"icd_o_3_morphology": "9673/3"},
        "line_of_therapy": 1,
        "biomarkers": {"BIO-CD20-IHC": "positive",
                       "BIO-TP53-MUTATION": "positive"},
        "demographics": {"age": 55, "sex": "male", "ecog": 0,
                         "fit_for_transplant": True},
        "findings": {},
    }
    plan = generate_plan(patient, kb_root=KB_ROOT)
    assert plan.disease_id == "DIS-MCL"
    # Even though patient is fit for transplant, TP53 routes to BTKi-R
    assert plan.default_indication_id == "IND-MCL-1L-BTKI-R"
