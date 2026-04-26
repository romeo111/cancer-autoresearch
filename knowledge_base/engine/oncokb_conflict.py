"""Resistance-conflict detector — safe-rollout v3 §6 (T3 mitigation).

Pure function. NO I/O. Detects when an engine-recommended drug appears
in OncoKB R1/R2 evidence for one of the patient's biomarkers.

This is the most safety-critical part of the OncoKB integration:
without it, a clinician scrolling top-down might miss resistance
evidence in the lower OncoKB section. Per CHARTER §15.2 C6
(automation-bias mitigation), conflicts must surface inline in the
track-card, not only in the OncoKB layer.

Wired by `generate_plan` after both `tracks` and `oncokb_layer.results`
are populated. Output drives:
  - inline banner in render (red R1, amber R2)
  - ProvenanceEvent("resistance_conflict_detected") on the plan
  - MDT trigger: molecular_geneticist role added (priority high for R1, medium for R2)
"""

from __future__ import annotations

from typing import Iterable

from .oncokb_types import (
    OncoKBLayer,
    OncoKBResult,
    RESISTANCE_LEVELS,
    ResistanceConflict,
)


def _drugs_from_track_regimen(regimen_data: dict | None) -> set[str]:
    """Extract drug names referenced by a regimen. Lower-cased for
    case-insensitive comparison with OncoKB drug names."""
    if not regimen_data:
        return set()
    out: set[str] = set()
    for comp in regimen_data.get("components") or []:
        if not isinstance(comp, dict):
            continue
        # Drug name as stored on the component (preferred name)
        name = comp.get("drug_name") or comp.get("name")
        if name:
            out.add(name.lower())
        # Drug ID — strip canonical prefix like "DRUG-VEMURAFENIB" → "vemurafenib"
        did = comp.get("drug_id")
        if did and isinstance(did, str):
            stripped = did.split("-", 1)[-1].lower() if did.startswith("DRUG-") else did.lower()
            out.add(stripped)
    return out


def detect_resistance_conflicts(
    tracks: Iterable,  # list[PlanTrack] — kept loose to avoid import cycle
    oncokb_results: list[OncoKBResult],
) -> list[ResistanceConflict]:
    """Pure. Returns conflicts where a track-recommended drug overlaps
    with OncoKB R1/R2 evidence for one of the patient's queried biomarkers.

    Comparison is case-insensitive. Both `drug_name` and `drug_id`
    (sans `DRUG-` prefix) on each regimen component are compared
    against OncoKB-reported drug names."""

    conflicts: list[ResistanceConflict] = []

    # Build (drug → list of (gene, variant, level, description)) index
    # from R1/R2 OncoKB results
    resistance_index: list[tuple[str, str, str, str, str | None]] = []
    for result in oncokb_results:
        for opt in result.therapeutic_options:
            if opt.level not in RESISTANCE_LEVELS:
                continue
            for drug in opt.drugs:
                resistance_index.append(
                    (
                        drug.lower(),
                        result.query.gene,
                        result.query.variant,
                        opt.level,
                        opt.description,
                    )
                )

    if not resistance_index:
        return conflicts

    seen: set[tuple[str, str, str, str, str]] = set()
    for track in tracks:
        track_id = getattr(track, "track_id", None) or "?"
        regimen = getattr(track, "regimen_data", None)
        track_drugs = _drugs_from_track_regimen(regimen)
        if not track_drugs:
            continue

        for drug_lower, gene, variant, level, description in resistance_index:
            if drug_lower not in track_drugs:
                continue
            key = (track_id, drug_lower, gene, variant, level)
            if key in seen:
                continue
            seen.add(key)
            conflicts.append(
                ResistanceConflict(
                    track_id=track_id,
                    drug=drug_lower,
                    gene=gene,
                    variant=variant,
                    level=level,
                    description=description,
                )
            )

    return conflicts


def annotate_layer_with_conflicts(
    layer: OncoKBLayer,
    tracks: Iterable,
) -> OncoKBLayer:
    """Convenience wrapper. Mutates and returns the layer for chaining."""
    layer.resistance_conflicts = detect_resistance_conflicts(tracks, layer.results)
    return layer


__all__ = [
    "detect_resistance_conflicts",
    "annotate_layer_with_conflicts",
]
