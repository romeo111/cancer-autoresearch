"""Plan entity — versioned per-patient treatment plan with multiple tracks.

A Plan is the **rendered output** of the rule engine for a specific patient
at a point in time. Per CHARTER §2, every Plan presents at least two
alternative tracks (standard, aggressive) in **one document** — easier for
tumor-board discussion, single revision history, single audit trail.

A Plan is also a **versioned, living artifact** (per the project's core
product vision): when new patient data arrives — fresh labs, doctor decision,
updated history, new imaging — a new Plan version is generated. The previous
version is retained (immutable), linked via supersedes/superseded_by.

**Privacy note:** Plan instances contain patient-specific data. They live
**outside** the public knowledge base (see CHARTER §9.3). Default location:
`patient_plans/<patient_id>/v<N>.yaml`, gitignored. Only the schema (this
file) and templates are in the public repo.

**FDA non-device CDS positioning** (CHARTER §15): the Plan output structure
is what makes OpenOnco satisfy §520(o)(1)(E) Criterion 4 — every Plan
surfaces the intended use, HCP user, patient population, algorithm summary,
data limitations, and per-track rationale + sources, so the HCP can
independently review the basis.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from .base import Base


class PlanTrack(Base):
    """One alternative treatment plan presented in the document.

    Tracks are not mutually exclusive in presentation — they're shown
    together. `is_default` marks the engine's current best selection;
    HCP makes the actual choice.
    """

    track_id: str  # "standard" | "aggressive" | "trial" | "palliative"
    label: str  # "Стандартний план"
    label_en: Optional[str] = None
    indication_id: str  # → Indication.id
    is_default: bool = False
    selection_reason: Optional[str] = None
    # Materialized at render time so the rendered document is self-contained
    indication_data: Optional[dict] = None
    regimen_data: Optional[dict] = None
    monitoring_data: Optional[dict] = None
    supportive_care_data: list[dict] = Field(default_factory=list)
    contraindications_data: list[dict] = Field(default_factory=list)


class PlanAnnotation(Base):
    """Clinician comment / revision request / approval / concern attached
    to the Plan or to a specific track. Append-only; resolution is a new
    annotation, not in-place edit."""

    track_id: Optional[str] = None  # null = annotation on whole plan
    author: str
    timestamp: str
    annotation_type: Literal["comment", "revision_request", "approval", "concern", "data_update"]
    text: str
    resolved_by: Optional[str] = None  # id of subsequent annotation that resolves this one


class FDAComplianceMetadata(Base):
    """Fields surfaced in every rendered Plan so an HCP can independently
    review the basis (FDA §520(o)(1)(E) Criterion 4 — see CHARTER §15)."""

    intended_use: str
    hcp_user_specification: str
    patient_population_match: str
    algorithm_summary: str
    data_sources_summary: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)
    automation_bias_warning: Optional[str] = None
    time_critical: bool = False  # if true, falls outside non-device CDS carve-out


class Plan(Base):
    id: str  # "PLAN-PZ-001-V1"
    patient_id: str  # "PZ-001"
    version: int = 1
    generated_at: str  # ISO-8601

    # Versioning chain (immutable history per CHARTER §10.2)
    supersedes: Optional[str] = None  # previous Plan id
    superseded_by: Optional[str] = None  # set when a newer version replaces this one
    revision_trigger: Optional[str] = None  # e.g. "new lab result 2026-05-01"

    # What the engine ran on
    patient_snapshot: dict
    algorithm_id: str
    knowledge_base_state: dict = Field(default_factory=dict)

    # The tracks — at least 2 per CHARTER §2
    tracks: list[PlanTrack]

    # FDA Criterion 4 metadata (always present, surfaced in rendered doc)
    fda_compliance: FDAComplianceMetadata

    # Engine internals (also surfaced for transparency)
    trace: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # Living document — append-only annotations
    annotations: list[PlanAnnotation] = Field(default_factory=list)
