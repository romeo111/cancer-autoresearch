"""RedFlag entity — KNOWLEDGE_SCHEMA_SPECIFICATION §9."""

from typing import Optional

from pydantic import Field

from .base import Base, RedFlagDirection, RedFlagSeverity


class RedFlagTrigger(Base):
    type: str  # symptom_composite | lab_value | imaging_finding | biomarker_threshold | ...
    all_of: list[dict] = Field(default_factory=list)
    any_of: list[dict] = Field(default_factory=list)
    none_of: list[dict] = Field(default_factory=list)


class RedFlag(Base):
    id: str
    definition: str
    definition_ua: Optional[str] = None

    trigger: RedFlagTrigger
    clinical_direction: RedFlagDirection

    # Conflict-resolution fields (added P0). When two or more RedFlags fire
    # with conflicting clinical_direction, the engine resolves by:
    #   1. clinical_direction precedence (hold > intensify > de_escalate > investigate)
    #   2. severity (critical > major > minor)
    #   3. priority (lower wins; default 100)
    severity: RedFlagSeverity = RedFlagSeverity.MAJOR
    priority: int = 100

    # Optional explicit branch wiring. When set, lets test/coverage tooling
    # confirm that this RedFlag actually drives a specific decision-tree
    # step.id in the named Algorithm. Pure metadata — engine still walks
    # the tree as authored. Format: {"ALGO-X": "step-id-or-int"}.
    branch_targets: dict[str, str] = Field(default_factory=dict)

    relevant_diseases: list[str] = Field(default_factory=list)  # ["*"] = universal
    shifts_algorithm: list[str] = Field(default_factory=list)  # Algorithm IDs affected

    sources: list[str] = Field(default_factory=list)
    last_reviewed: Optional[str] = None
    notes: Optional[str] = None

    # Authoring lifecycle. Drafts (`draft: true`) are loaded by the engine
    # but flagged in CI; non-draft RedFlags must satisfy the source-citation
    # requirement (CHARTER §6.1) and pass clinical review.
    draft: bool = False
