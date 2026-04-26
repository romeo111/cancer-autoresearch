"""Phase 6 — RedFlag conflict-resolution stress tests.

Three deterministic conflict scenarios that exercise the
`resolve_redflag_conflict` precedence chain:

  1. clinical_direction: hold > intensify > de-escalate > investigate
  2. severity: critical > major > minor
  3. priority: lower numeric wins
  4. id: lexicographic tie-break

Each scenario:
- Defines a synthetic patient profile that fires multiple RFs.
- Asserts the engine's algorithm trace records all expected RFs.
- Asserts the resolved winner matches the deterministic precedence.

These are the regression sentinels the RedFlag-quality plan §6 calls for.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from knowledge_base.engine.redflag_eval import (
    evaluate_redflag_trigger,
    resolve_redflag_conflict,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
KB_ROOT = REPO_ROOT / "knowledge_base" / "hosted" / "content"


def _all_redflags() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in (KB_ROOT / "redflags").rglob("*.yaml"):
        with p.open(encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
        if d.get("id"):
            out[d["id"]] = d
    return out


# ── Scenario 1 ──────────────────────────────────────────────────────────────
# DLBCL high-IPI (intensify) + HBsAg+ (universal HBV, hold)
# → hold direction wins; engine's plan should reflect the prophylaxis
# pathway taking precedence over Pola-R-CHP intensification.


def test_conflict_hold_outranks_intensify_dlbcl_hbsag_high_ipi():
    rfs = _all_redflags()
    findings = {
        # high IPI: age + ECOG + LDH + stage + extranodal
        "high_ipi": True,
        "ipi_score": 4,
        # HBV reactivation risk
        "hbsag": "positive",
    }

    # Both should fire on these findings
    fired_ids = []
    for rf_id, rf in rfs.items():
        if evaluate_redflag_trigger(rf.get("trigger") or {}, findings):
            fired_ids.append(rf_id)

    assert "RF-DLBCL-HIGH-IPI" in fired_ids, (
        f"Expected RF-DLBCL-HIGH-IPI to fire on these findings; "
        f"fired: {fired_ids}"
    )
    assert "RF-UNIVERSAL-HBV-REACTIVATION-RISK" in fired_ids, (
        f"Expected RF-UNIVERSAL-HBV-REACTIVATION-RISK to fire; "
        f"fired: {fired_ids}"
    )

    # Resolve: hold > intensify, so HBV wins.
    winner, ordered = resolve_redflag_conflict(
        ["RF-DLBCL-HIGH-IPI", "RF-UNIVERSAL-HBV-REACTIVATION-RISK"],
        rfs,
    )
    assert winner == "RF-UNIVERSAL-HBV-REACTIVATION-RISK", (
        f"Expected hold-direction RF to win conflict resolution; got {winner}. "
        f"Full ordering: {ordered}"
    )


# ── Scenario 2 ──────────────────────────────────────────────────────────────
# DLBCL frailty (de-escalate, severity major) +
# DLBCL high-risk-biology (intensify, severity critical)
# → directions conflict; intensify ≻ de-escalate per direction precedence.


def test_conflict_intensify_outranks_deescalate_dlbcl_frailty_biology():
    rfs = _all_redflags()
    findings = {
        # frailty
        "age": 80,
        "comorbidity_grade2_count": 2,
        "ecog": 3,
        # high-risk biology
        "double_expressor_status": True,
    }

    fired = [
        rf_id
        for rf_id, rf in rfs.items()
        if evaluate_redflag_trigger(rf.get("trigger") or {}, findings)
    ]
    assert "RF-DLBCL-FRAILTY-AGE" in fired
    assert "RF-DLBCL-HIGH-RISK-BIOLOGY" in fired

    winner, ordered = resolve_redflag_conflict(
        ["RF-DLBCL-FRAILTY-AGE", "RF-DLBCL-HIGH-RISK-BIOLOGY"], rfs
    )
    assert winner == "RF-DLBCL-HIGH-RISK-BIOLOGY", (
        f"Expected intensify (critical) to outrank de-escalate (major); "
        f"got {winner}; full ordering: {ordered}"
    )


# ── Scenario 3 ──────────────────────────────────────────────────────────────
# Two intensify RFs, equal direction.
# Tie broken by severity.


def test_conflict_severity_tiebreaker_when_directions_equal():
    rfs = _all_redflags()
    # Both intensify: high-risk-biology (critical) + high-IPI (major)
    winner, ordered = resolve_redflag_conflict(
        ["RF-DLBCL-HIGH-IPI", "RF-DLBCL-HIGH-RISK-BIOLOGY"], rfs
    )
    bio = rfs["RF-DLBCL-HIGH-RISK-BIOLOGY"]
    ipi = rfs["RF-DLBCL-HIGH-IPI"]
    assert bio["clinical_direction"] == ipi["clinical_direction"] == "intensify"
    assert bio["severity"] == "critical"
    # Whichever has higher severity wins; if both same, priority breaks tie.
    if ipi.get("severity") == "critical":
        # Same severity → priority decides
        if ipi.get("priority", 100) < bio.get("priority", 100):
            assert winner == "RF-DLBCL-HIGH-IPI"
        else:
            assert winner == "RF-DLBCL-HIGH-RISK-BIOLOGY"
    else:
        assert winner == "RF-DLBCL-HIGH-RISK-BIOLOGY", (
            f"Expected critical-severity to outrank major; got {winner}; "
            f"ordering {ordered}"
        )


# ── Scenario 4 ──────────────────────────────────────────────────────────────
# Universal TLS-RISK (intensify) + DLBCL FRAILTY-AGE (de-escalate).
# Direction precedence: intensify ≻ de-escalate, so TLS wins.


def test_conflict_universal_tls_vs_disease_specific_frailty():
    rfs = _all_redflags()
    findings = {
        # TLS risk
        "ldh_ratio_to_uln": 3.0,
        "absolute_lymphocyte_count_k_ul": 30,
        # Frailty
        "ecog": 3,
        "age": 81,
        "comorbidity_grade2_count": 2,
    }

    fired = [
        rf_id
        for rf_id, rf in rfs.items()
        if evaluate_redflag_trigger(rf.get("trigger") or {}, findings)
    ]
    assert "RF-UNIVERSAL-TLS-RISK" in fired
    assert "RF-DLBCL-FRAILTY-AGE" in fired

    winner, _ = resolve_redflag_conflict(
        ["RF-UNIVERSAL-TLS-RISK", "RF-DLBCL-FRAILTY-AGE"], rfs
    )
    assert winner == "RF-UNIVERSAL-TLS-RISK", (
        f"Expected intensify (TLS) to outrank de-escalate (frailty); got {winner}"
    )


# ── Scenario 5 ──────────────────────────────────────────────────────────────
# Three-way conflict to verify ordered list is fully sorted.


def test_three_way_conflict_full_ordering():
    rfs = _all_redflags()
    rf_ids = [
        "RF-UNIVERSAL-HBV-REACTIVATION-RISK",  # hold / critical / 50
        "RF-DLBCL-HIGH-RISK-BIOLOGY",          # intensify / critical / 80
        "RF-DLBCL-FRAILTY-AGE",                # de-escalate / major / 90
    ]
    winner, ordered = resolve_redflag_conflict(rf_ids, rfs)

    assert winner == "RF-UNIVERSAL-HBV-REACTIVATION-RISK"
    assert ordered == [
        "RF-UNIVERSAL-HBV-REACTIVATION-RISK",   # hold first
        "RF-DLBCL-HIGH-RISK-BIOLOGY",           # intensify second
        "RF-DLBCL-FRAILTY-AGE",                 # de-escalate last
    ], f"Expected fully sorted by direction precedence; got {ordered}"


# ── 2L+/relapsed heme scenarios (HEME ALGO-C) ───────────────────────────────
# Conflict-resolution stress tests for 2L+/relapsed multi-RF patterns. These
# exercise the same precedence chain in salvage / refractory contexts where
# multiple intensify-direction RFs compete for the algorithm's attention.


# ── Scenario 6 ──────────────────────────────────────────────────────────────
# DLBCL 2L chemorefractory: RF-DLBCL-HIGH-IPI (intensify, major) +
# RF-AGGRESSIVE-HISTOLOGY-TRANSFORMATION (intensify) both fire.
# Both directions equal → severity / priority break the tie. Expected: the RF
# with higher severity / lower priority wins; either way the winner direction
# stays "intensify" (no de-escalation) — verifying salvage-track stays hot.


def test_conflict_2l_dlbcl_chemorefractory_with_high_ipi():
    rfs = _all_redflags()
    findings = {
        # high IPI persists in 2L
        "high_ipi": True,
        "ipi_score": 4,
        # transformation evidence: biopsy + LDH + rapid clinical progression
        "biopsy_shows_dlbcl": True,
        "ldh_ratio_to_uln": 2.1,
        "clinical_progression_weeks": 6,
    }

    fired = [
        rf_id
        for rf_id, rf in rfs.items()
        if evaluate_redflag_trigger(rf.get("trigger") or {}, findings)
    ]
    assert "RF-DLBCL-HIGH-IPI" in fired, (
        f"Expected RF-DLBCL-HIGH-IPI to fire on 2L chemorefractory profile; "
        f"fired: {fired}"
    )
    assert "RF-AGGRESSIVE-HISTOLOGY-TRANSFORMATION" in fired, (
        f"Expected RF-AGGRESSIVE-HISTOLOGY-TRANSFORMATION to fire on biopsy + "
        f"LDH + rapid progression; fired: {fired}"
    )

    winner, ordered = resolve_redflag_conflict(
        ["RF-DLBCL-HIGH-IPI", "RF-AGGRESSIVE-HISTOLOGY-TRANSFORMATION"], rfs
    )
    # Both intensify → same direction precedence; severity / priority decides.
    high_ipi = rfs["RF-DLBCL-HIGH-IPI"]
    transform = rfs["RF-AGGRESSIVE-HISTOLOGY-TRANSFORMATION"]
    assert (
        high_ipi["clinical_direction"]
        == transform["clinical_direction"]
        == "intensify"
    )
    # Whichever wins, the winner must keep "intensify" — never de-escalate.
    assert rfs[winner]["clinical_direction"] == "intensify", (
        f"Expected intensify-direction winner in 2L chemorefractory conflict; "
        f"got {winner} with direction {rfs[winner]['clinical_direction']}; "
        f"ordered: {ordered}"
    )


# ── Scenario 7 ──────────────────────────────────────────────────────────────
# MM 2L progression with RF-MM-RENAL-DYSFUNCTION (investigate, organ-dysfunction)
# + RF-MM-HIGH-RISK-CYTOGENETICS (intensify, high-risk-biology).
# Direction precedence: intensify ≻ investigate, so cytogenetics wins.
# This protects against renal-dysfunction silently down-graders the regimen
# tier when high-risk biology demands the aggressive triplet.


def test_conflict_2l_mm_relapse_with_renal_dysfunction():
    rfs = _all_redflags()
    findings = {
        # renal dysfunction (myeloma kidney)
        "creatinine_clearance_ml_min": 38,
        "serum_creatinine_mg_dl": 2.4,
        "mm_renal_failure": True,
        # high-risk cytogenetics
        "del_17p": True,
        "tp53_mutation": True,
        "gain_1q": True,
        "mm_cytogenetics_high_risk": True,
    }

    fired = [
        rf_id
        for rf_id, rf in rfs.items()
        if evaluate_redflag_trigger(rf.get("trigger") or {}, findings)
    ]
    assert "RF-MM-RENAL-DYSFUNCTION" in fired, (
        f"Expected RF-MM-RENAL-DYSFUNCTION to fire on CrCl<60 / Cr>2; "
        f"fired: {fired}"
    )
    assert "RF-MM-HIGH-RISK-CYTOGENETICS" in fired, (
        f"Expected RF-MM-HIGH-RISK-CYTOGENETICS to fire on del(17p) + "
        f"TP53-mut + gain1q; fired: {fired}"
    )

    winner, ordered = resolve_redflag_conflict(
        ["RF-MM-RENAL-DYSFUNCTION", "RF-MM-HIGH-RISK-CYTOGENETICS"], rfs
    )
    assert winner == "RF-MM-HIGH-RISK-CYTOGENETICS", (
        f"Expected intensify (cytogenetics) to outrank investigate "
        f"(renal dysfunction) per direction precedence; got {winner}; "
        f"ordering: {ordered}"
    )


# ── Scenario 8 ──────────────────────────────────────────────────────────────
# AML 2L with RF-AML-FLT3-ACTIONABLE (intensify, major) +
# RF-AML-HIGH-RISK-BIOLOGY (intensify, critical) both firing.
# Same direction → severity tiebreak: critical ≻ major ⇒ HIGH-RISK-BIOLOGY wins.
# This protects against FLT3-only thinking when adverse cytogenetics also
# present — alloHCT-bridge urgency must dominate.


def test_conflict_aml_flt3_with_high_risk_biology():
    rfs = _all_redflags()
    findings = {
        # FLT3 actionable
        "flt3_itd": True,
        "flt3_mutation": "positive",
        # ELN-2022 adverse-risk biology
        "tp53_mutation": True,
        "complex_karyotype": True,
        "monosomal_karyotype": True,
        "aml_eln_risk": "adverse",
    }

    fired = [
        rf_id
        for rf_id, rf in rfs.items()
        if evaluate_redflag_trigger(rf.get("trigger") or {}, findings)
    ]
    assert "RF-AML-FLT3-ACTIONABLE" in fired, (
        f"Expected RF-AML-FLT3-ACTIONABLE to fire on FLT3-ITD; fired: {fired}"
    )
    assert "RF-AML-HIGH-RISK-BIOLOGY" in fired, (
        f"Expected RF-AML-HIGH-RISK-BIOLOGY to fire on TP53-mut + complex "
        f"karyotype + adverse ELN; fired: {fired}"
    )

    winner, ordered = resolve_redflag_conflict(
        ["RF-AML-FLT3-ACTIONABLE", "RF-AML-HIGH-RISK-BIOLOGY"], rfs
    )
    flt3 = rfs["RF-AML-FLT3-ACTIONABLE"]
    bio = rfs["RF-AML-HIGH-RISK-BIOLOGY"]
    assert flt3["clinical_direction"] == bio["clinical_direction"] == "intensify"
    # Severity tiebreak: critical ≻ major → HIGH-RISK-BIOLOGY wins.
    assert bio["severity"] == "critical"
    assert flt3["severity"] == "major"
    assert winner == "RF-AML-HIGH-RISK-BIOLOGY", (
        f"Expected critical-severity (HIGH-RISK-BIOLOGY) to outrank major "
        f"(FLT3-ACTIONABLE) when directions are equal; got {winner}; "
        f"ordering: {ordered}"
    )
