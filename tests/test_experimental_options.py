"""Phase C tracer-bullet tests for the experimental-options enumerator.

Plan: docs/plans/ua_ingestion_and_alternatives_2026-04-26.md §3.3 + §5.4.
Module: knowledge_base/engine/experimental_options.py

Five behaviours validated here:
  1. With a stub search_fn, recruiting trials are returned as ExperimentalTrial.
  2. Closed-enrollment statuses (COMPLETED / TERMINATED) are filtered out.
  3. UA-site presence is surfaced via `sites_ua` when ctgov reports a UA country.
  4. ctgov failures + no-search-fn return an empty bundle, never raise — per
     plan §3.3 ("Не падає"). This protects the engine when offline.
  5. Cache returns the same option for the same query signature.

Architectural invariant (CHARTER §8.3 + feedback_efficacy_over_registration.md):
the enumerator is render-time metadata only. It exposes alternatives; it
never changes which Indication the engine selects. That invariant is
guarded by `tests/test_plan_invariant_ua_availability.py`; this file
just validates the enumerator's contract.
"""

from __future__ import annotations

import pytest

from knowledge_base.engine import (
    clear_experimental_cache,
    enumerate_experimental_options,
)
from knowledge_base.engine.experimental_options import TrialQuery
from knowledge_base.schemas.experimental_option import ExperimentalOption


def _study(
    nct_id: str,
    *,
    status: str = "RECRUITING",
    title: str = "Sample trial",
    countries: list[str] | None = None,
    eligibility: str = "",
    phase: str = "PHASE2",
    sponsor: str = "Acme Onc",
) -> dict:
    """Mimics one entry returned by ctgov_client.search_trials."""
    return {
        "nct_id": nct_id,
        "title": title,
        "status": status,
        "phase": phase,
        "sponsor": sponsor,
        "summary": "Brief summary.",
        "eligibility_criteria": eligibility,
        "countries": countries or [],
    }


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_experimental_cache()
    yield
    clear_experimental_cache()


# ── 1. Happy path ───────────────────────────────────────────────────────


def test_enumerate_returns_recruiting_trials():
    studies = [
        _study("NCT00000001", title="FLAURA2", phase="PHASE3"),
        _study("NCT00000002", title="MARIPOSA", phase="PHASE3"),
    ]
    opt = enumerate_experimental_options(
        disease_id="DIS-NSCLC",
        disease_term="Non-small cell lung cancer",
        biomarker_profile="EGFR mutation",
        line_of_therapy=1,
        search_fn=lambda **_: studies,
    )

    assert isinstance(opt, ExperimentalOption)
    assert opt.id.startswith("EXPER-DIS-NSCLC-EGFR_MUTATION-L1-")
    assert opt.disease_id == "DIS-NSCLC"
    assert opt.molecular_subtype == "EGFR mutation"
    assert opt.line_of_therapy == 1
    assert [t.nct_id for t in opt.trials] == ["NCT00000001", "NCT00000002"]
    assert opt.trials[0].title == "FLAURA2"
    assert opt.trials[0].phase == "PHASE3"
    assert opt.last_synced is not None


# ── 2. Status filter ────────────────────────────────────────────────────


def test_closed_enrollment_studies_are_filtered():
    studies = [
        _study("NCT-OPEN", status="RECRUITING"),
        _study("NCT-DONE", status="COMPLETED"),
        _study("NCT-TERM", status="TERMINATED"),
        _study("NCT-WITH", status="WITHDRAWN"),
        _study("NCT-INV",  status="ENROLLING_BY_INVITATION"),
        _study("NCT-ACT",  status="ACTIVE_NOT_RECRUITING"),
    ]
    opt = enumerate_experimental_options(
        disease_id="DIS-MM",
        disease_term="Multiple myeloma",
        search_fn=lambda **_: studies,
    )
    surfaced = {t.nct_id for t in opt.trials}
    assert surfaced == {"NCT-OPEN", "NCT-INV", "NCT-ACT"}


# ── 3. UA-site enrichment ───────────────────────────────────────────────


def test_ua_country_surfaces_in_sites_ua():
    studies = [
        _study("NCT-UA",   countries=["US", "UA", "DE"]),
        _study("NCT-NOUA", countries=["US", "DE"]),
        _study("NCT-NAME", countries=["Ukraine"]),  # full name, not ISO
    ]
    opt = enumerate_experimental_options(
        disease_id="DIS-CLL",
        disease_term="Chronic lymphocytic leukemia",
        search_fn=lambda **_: studies,
    )
    by_id = {t.nct_id: t for t in opt.trials}
    assert by_id["NCT-UA"].sites_ua == ["UA"]
    assert by_id["NCT-NOUA"].sites_ua == []
    assert by_id["NCT-NAME"].sites_ua == ["UA"]
    # Full country list still preserved on every trial
    assert by_id["NCT-UA"].countries == ["US", "UA", "DE"]


# ── 4. Eligibility split ────────────────────────────────────────────────


def test_eligibility_text_split_into_inclusion_and_exclusion():
    elig = (
        "Inclusion Criteria:\n- Age >= 18\n- ECOG 0-1\n\n"
        "Exclusion Criteria:\n- Active CNS disease\n- Prior anti-PD1"
    )
    studies = [_study("NCT-E", eligibility=elig)]
    opt = enumerate_experimental_options(
        disease_id="DIS-NSCLC",
        disease_term="NSCLC",
        search_fn=lambda **_: studies,
    )
    t = opt.trials[0]
    assert t.inclusion_summary is not None and "ECOG 0-1" in t.inclusion_summary
    assert t.exclusion_summary is not None and "Active CNS" in t.exclusion_summary


# ── 5. Offline / failure-path safety ────────────────────────────────────


def test_no_search_fn_returns_empty_bundle_with_note():
    opt = enumerate_experimental_options(
        disease_id="DIS-NSCLC",
        disease_term="NSCLC",
    )
    assert opt.trials == []
    assert opt.notes is not None and "ctgov search not configured" in opt.notes


def test_search_fn_exception_returns_empty_bundle_with_note():
    def _boom(**_):
        raise RuntimeError("network down")

    opt = enumerate_experimental_options(
        disease_id="DIS-NSCLC",
        disease_term="NSCLC",
        search_fn=_boom,
    )
    assert opt.trials == []
    assert opt.notes is not None and "ctgov search failed" in opt.notes
    assert "network down" in opt.notes


# ── 6. Cache behaviour ──────────────────────────────────────────────────


def test_cache_returns_same_option_for_same_query():
    call_count = {"n": 0}

    def _counting_fn(**_):
        call_count["n"] += 1
        return [_study("NCT-1")]

    o1 = enumerate_experimental_options(
        disease_id="DIS-X",
        disease_term="x cancer",
        biomarker_profile="BRCA1",
        line_of_therapy=2,
        search_fn=_counting_fn,
    )
    o2 = enumerate_experimental_options(
        disease_id="DIS-X",
        disease_term="x cancer",
        biomarker_profile="BRCA1",
        line_of_therapy=2,
        search_fn=_counting_fn,
    )
    assert call_count["n"] == 1, "cache should suppress the second call"
    assert o1 is o2

    # Different signature → fresh call
    enumerate_experimental_options(
        disease_id="DIS-X",
        disease_term="x cancer",
        biomarker_profile="BRCA2",
        line_of_therapy=2,
        search_fn=_counting_fn,
    )
    assert call_count["n"] == 2


def test_query_signature_is_stable():
    a = TrialQuery(disease_term="NSCLC", biomarker_term="EGFR", line_of_therapy=1)
    b = TrialQuery(disease_term="NSCLC", biomarker_term="EGFR", line_of_therapy=1)
    c = TrialQuery(disease_term="NSCLC", biomarker_term="EGFR", line_of_therapy=2)
    assert a.signature() == b.signature()
    assert a.signature() != c.signature()
