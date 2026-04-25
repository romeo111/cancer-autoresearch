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
