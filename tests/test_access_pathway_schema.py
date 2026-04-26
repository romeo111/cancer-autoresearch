"""Phase D groundwork — AccessPathway schema scaffolding.

Tests the Pydantic model only. Content YAML + validator + render are
follow-up PRs (plan §5.5 + §4 Access Matrix block).

Engine-side: AccessPathway is render-time-only metadata. The schema
exists so a curated content layer can be added without further engine
changes; this PR ships nothing under `hosted/content/access_pathways/`
yet — that's the clinical-authoring task in plan §5.5 (≈30 entries
seeded for non-reimbursed drugs: T-DXd, Lu-PSMA, CDK4/6i, etc.).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from knowledge_base.schemas import AccessPathway, CostOrientation


def test_minimal_valid_pathway():
    p = AccessPathway(
        id="PATH-LU-PSMA-INTERNATIONAL-EU",
        name="Lu-177-PSMA via international referral (EU)",
        applies_to_drug_ids=["DRUG-LUTETIUM-177-PSMA"],
        pathway_type="international_referral",
    )
    assert p.id == "PATH-LU-PSMA-INTERNATIONAL-EU"
    assert p.applies_to_drug_ids == ["DRUG-LUTETIUM-177-PSMA"]
    assert p.applies_to_regimen_ids == []
    assert p.cost_orientation is None
    assert p.country_options == []


def test_full_pathway_with_cost_and_caveats():
    p = AccessPathway(
        id="PATH-OSIMERTINIB-FOUNDATION",
        name="Osimertinib via Tabletochki foundation",
        name_ua="Осимертиніб через фонд Табле́точки",
        applies_to_drug_ids=["DRUG-OSIMERTINIB"],
        pathway_type="foundation",
        country_options=["UA"],
        cost_orientation=CostOrientation(
            currency="UAH", min=0.0, max=15000.0, per_unit="month",
            notes="Co-pay only; foundation covers bulk."
        ),
        typical_lead_time_weeks=[2, 6],
        contact_pattern="Direct application via foundation portal.",
        eligibility_caveats=[
            "EGFR-mut NSCLC confirmed by accredited lab",
            "Income threshold per foundation policy",
        ],
        requires_documentation=[
            "Pathology report",
            "ICD-10 code C34.x on referral",
        ],
        verified_by="dr-tymoshenko",
        last_verified="2026-04-26",
        sources=["SRC-TABLETOCHKI-PORTAL"],
    )
    assert p.cost_orientation is not None
    assert p.cost_orientation.currency == "UAH"
    assert p.cost_orientation.max == 15000.0
    assert p.typical_lead_time_weeks == [2, 6]
    assert len(p.eligibility_caveats) == 2


def test_id_required():
    with pytest.raises(ValidationError):
        AccessPathway(
            name="Missing id pathway",
            pathway_type="self_pay",
        )


def test_pathway_type_is_freeform_but_documented():
    """`pathway_type` is a `str` (not enum) for forward-compat with new
    routes — the docstring lists the canonical set, and a future
    validator can warn on unknown values without breaking schema load."""

    p = AccessPathway(
        id="PATH-X",
        name="x",
        pathway_type="some_future_route",  # accepted; validator gate is separate
    )
    assert p.pathway_type == "some_future_route"


def test_cost_orientation_min_max_optional():
    """Single-point estimates allowed (currency only)."""
    c = CostOrientation(currency="EUR")
    assert c.currency == "EUR"
    assert c.min is None
    assert c.max is None


def test_entity_dir_registry_includes_access_pathways():
    """Loader picks up `hosted/content/access_pathways/` once content is
    seeded."""
    from knowledge_base.schemas import ENTITY_BY_DIR

    assert "access_pathways" in ENTITY_BY_DIR
    assert ENTITY_BY_DIR["access_pathways"] is AccessPathway
