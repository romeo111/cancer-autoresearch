"""AccessPathway — how a non-reimbursed drug actually reaches a patient in Ukraine.

Per docs/plans/ua_ingestion_and_alternatives_2026-04-26.md §2.1 + §5.5.

A patient-access pathway entity describing one route by which a drug or
regimen — typically guideline-endorsed but not registered in Ukraine
or not reimbursed by НСЗУ — can be obtained: charitable foundation,
compassionate-use program, international referral, humanitarian import,
self-pay, or a clinical trial.

Engine semantics (CHARTER §8.3 + plan §3.2 invariant): `AccessPathway`
is render-time-only metadata. The engine NEVER reads pathway availability
as a selection signal — clinicians see all guideline-endorsed options
regardless of how easily reachable they are. The pathway data only
informs the Access Matrix block in the rendered Plan.

Authoring: per CHARTER §6.1, two clinical-admin reviewers must approve
each pathway entry. The `verified_by` + `last_verified` fields gate a
quarterly freshness review (plan §6.4).
"""

from typing import Optional

from pydantic import Field

from .base import Base


class CostOrientation(Base):
    """Range-based cost estimate. Currency is mandatory; min/max optional
    when only a single point estimate is available. `per_unit` is one of
    `cycle | course | month | dose` — not a free-form string, but kept
    permissive (Base = `extra=allow`) to not break older YAML."""

    currency: str  # ISO-4217: UAH | EUR | USD
    min: Optional[float] = None
    max: Optional[float] = None
    per_unit: Optional[str] = None  # cycle | course | month | dose
    notes: Optional[str] = None


class AccessPathway(Base):
    """One reimbursement-bypass route for one or more drugs / regimens."""

    id: str
    name: str
    name_ua: Optional[str] = None

    # What the pathway covers (≥1 drug or regimen)
    applies_to_drug_ids: list[str] = Field(default_factory=list)
    applies_to_regimen_ids: list[str] = Field(default_factory=list)

    # How it works
    pathway_type: str
    # Valid values:
    #   foundation              — charity org (Tabletochki, Patients of Ukraine)
    #   compassionate_use       — pharma program (named-patient supply)
    #   international_referral  — patient travels to EU/US center
    #   humanitarian_import     — one-time import permit
    #   self_pay                — out-of-pocket, in-country pharmacy
    #   clinical_trial          — trial sponsor supplies the drug

    country_options: list[str] = Field(default_factory=list)  # ISO-3166-1 alpha-2

    cost_orientation: Optional[CostOrientation] = None
    typical_lead_time_weeks: Optional[list[int]] = None  # [min, max]

    contact_pattern: Optional[str] = None  # how a clinician initiates the request
    eligibility_caveats: list[str] = Field(default_factory=list)
    requires_documentation: list[str] = Field(default_factory=list)

    # Freshness audit
    verified_by: Optional[str] = None       # reviewer id
    last_verified: Optional[str] = None     # ISO date

    # Provenance
    sources: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
