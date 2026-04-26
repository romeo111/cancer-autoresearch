"""ExperimentalOption — clinical-trial track in a Plan.

Per docs/plans/ua_ingestion_and_alternatives_2026-04-26.md §2.3.

A single-(disease, biomarker_profile, line_of_therapy) container holding
the active recruiting / active-not-recruiting trials returned from
ClinicalTrials.gov. Generated, not curated. Render exposes these as a
third Plan track alongside the engine-selected standard + alternative.

Engine semantics: `ExperimentalOption` is render-time-only metadata. It
NEVER influences which Indication / Regimen the engine picks for the
default or alternative tracks (CHARTER §8.3 + the "show all alternatives"
invariant from `feedback_efficacy_over_registration.md`).
"""

from typing import Optional

from pydantic import Field

from .base import Base


class ExperimentalTrial(Base):
    """One ClinicalTrials.gov study entry, parsed from the v2 API."""

    nct_id: str
    title: str
    status: str  # "RECRUITING" | "ACTIVE_NOT_RECRUITING" | other
    phase: Optional[str] = None
    sponsor: Optional[str] = None
    summary: Optional[str] = None
    inclusion_summary: Optional[str] = None
    exclusion_summary: Optional[str] = None
    countries: list[str] = Field(default_factory=list)  # ISO-2 codes from ctgov
    sites_ua: list[str] = Field(default_factory=list)   # UA city names if any
    sites_global_count: Optional[int] = None
    last_synced: Optional[str] = None  # ISO date


class ExperimentalOption(Base):
    """One bundle of trials for a (disease, biomarker, stage, line) scenario.

    Generated via `enumerate_experimental_options()`; the `id` is
    deterministic from the query parameters so re-querying produces a
    stable identifier for caching + provenance.
    """

    id: str
    disease_id: str
    molecular_subtype: Optional[str] = None
    stage_stratum: Optional[str] = None
    line_of_therapy: Optional[int] = None
    trials: list[ExperimentalTrial] = Field(default_factory=list)
    last_synced: Optional[str] = None
    notes: Optional[str] = None
    sources: list[str] = Field(default_factory=lambda: ["SRC-CTGOV"])
