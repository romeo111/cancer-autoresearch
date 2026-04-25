"""Generate RedFlag scaffolds for the 15 zero-coverage diseases.

Outputs 75 YAML files (15 diseases × 5 RedFlag categories per
specs/REDFLAG_AUTHORING_GUIDE.md §2). Every scaffold is marked
`draft: true` and `last_reviewed: null` so the CI contract pass logs
them as drafts (visible debt) without failing the build.

What this script does NOT do — by design (CHARTER §8.3):

  - Invent clinical triggers (specific lab thresholds, biomarker cutoffs,
    composite-score formulas)
  - Pick which Algorithm decision_tree step each RF should drive
  - Choose appropriate sources for each scaffold (sources are left as
    a TODO sentinel SRC-TODO; CI will warn until a real source is added)

The clinician fills those in. This script just lays down the structure
+ disease/algorithm wiring + canonical naming so authoring is faster.

Usage:
    python scripts/scaffold_redflags.py
    python scripts/scaffold_redflags.py --dry-run     # don't write files
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
RF_DIR = REPO_ROOT / "knowledge_base" / "hosted" / "content" / "redflags"

# Each disease -> (algorithm_id, short-id-for-filename, human label).
ZERO_COVERAGE_DISEASES: list[tuple[str, str, str, str]] = [
    ("DIS-T-PLL",       "ALGO-T-PLL-1L",       "t_pll",       "T-PLL"),
    ("DIS-T-ALL",       "ALGO-T-ALL-1L",       "t_all",       "T-ALL"),
    ("DIS-PCNSL",       "ALGO-PCNSL-1L",       "pcnsl",       "PCNSL"),
    ("DIS-SPLENIC-MZL", "ALGO-SMZL-1L",        "smzl",        "Splenic MZL"),
    ("DIS-PTLD",        "ALGO-PTLD-1L",        "ptld",        "PTLD"),
    ("DIS-PMBCL",       "ALGO-PMBCL-1L",       "pmbcl",       "PMBCL"),
    ("DIS-B-ALL",       "ALGO-B-ALL-1L",       "b_all",       "B-ALL"),
    ("DIS-ATLL",        "ALGO-ATLL-1L",        "atll",        "ATLL"),
    ("DIS-EATL",        "ALGO-EATL-1L",        "eatl",        "EATL"),
    ("DIS-HCL",         "ALGO-HCL-1L",         "hcl",         "HCL"),
    ("DIS-HGBL-DH",     "ALGO-HGBL-DH-1L",     "hgbl_dh",     "HGBL-DH/-TH"),
    ("DIS-HSTCL",       "ALGO-HSTCL-1L",       "hstcl",       "HSTCL"),
    ("DIS-NK-T-NASAL",  "ALGO-NK-T-NASAL-1L",  "nk_t_nasal",  "NK/T-cell nasal"),
    ("DIS-NLPBL",       "ALGO-NLPBL-1L",       "nlpbl",       "NLPBL"),
    ("DIS-NODAL-MZL",   "ALGO-NMZL-1L",        "nmzl",        "Nodal MZL"),
]

# Category -> (suffix, default direction, default severity, hint trigger
# placeholder, notes hint).
# These are GENERIC scaffolds. Clinician must replace TODO placeholders.
CATEGORIES: list[tuple[str, str, str, str, str, str]] = [
    (
        "ORGAN-DYSFUNCTION",
        "organ_dysfunction",
        "de-escalate",
        "major",
        "creatinine_clearance_ml_min",
        "Generic organ-dysfunction stub. Common dose-modifying axes: CrCl<30, "
        "Child-Pugh B/C, LVEF<50%, bilirubin>3xULN, DLCO<60%. Pick the axis "
        "that drives this disease's regimen choice and replace the trigger.",
    ),
    (
        "INFECTION-SCREENING",
        "infection_screening",
        "hold",
        "major",
        "hbv_surface_antigen",
        "Pre-treatment infection screen. For anti-CD20 / BTKi / autoSCT-bound "
        "regimens, screen HBV (surface antigen + core Ab), HCV, HIV, latent "
        "TB. Replace placeholder finding with disease-specific dominant risk.",
    ),
    (
        "HIGH-RISK-BIOLOGY",
        "high_risk_biology",
        "intensify",
        "critical",
        "tp53_mutation",
        "High-risk biology that triggers regimen escalation. Common: TP53/del17p, "
        "MYC rearrangement, double-/triple-hit, blastoid morphology, Ph-like, "
        "Ki67>30%. Pick the biology that defines high-risk for this disease.",
    ),
    (
        "TRANSFORMATION-PROGRESSION",
        "transformation_progression",
        "intensify",
        "major",
        "rapid_progression_on_therapy",
        "Transformation or rapid-progression flag. Triggers regimen change "
        "(typically toward salvage / high-intensity arm). Disease-specific "
        "definition required (histologic transformation, PET-progression "
        "during therapy, new EN-localization).",
    ),
    (
        "FRAILTY-AGE",
        "frailty_age",
        "de-escalate",
        "major",
        "ecog_status",
        "Frailty / age-based de-escalation. Common: ECOG>=3, OR (age>=75 + "
        ">=2 comorbidities + albumin<3.5). Pick the disease-specific frailty "
        "rule that triggers reduced-intensity 1L regimen.",
    ),
]


def scaffold_yaml(
    disease_id: str,
    algorithm_id: str,
    disease_label: str,
    cat_suffix: str,
    cat_filename_part: str,
    direction: str,
    severity: str,
    finding_placeholder: str,
    notes_hint: str,
    short: str,
) -> tuple[str, str]:
    rf_id = f"RF-{disease_id.removeprefix('DIS-')}-{cat_suffix}"
    filename = f"rf_{short}_{cat_filename_part}.yaml"

    # Direction-specific concrete trigger templates so the YAML is at
    # least machine-evaluable as authored. Clinician will replace these
    # with disease-specific predicates from cited guidelines.
    if cat_suffix == "ORGAN-DYSFUNCTION":
        trigger_yaml = (
            "trigger:\n"
            "  type: lab_value\n"
            "  any_of:\n"
            f"    - finding: \"{finding_placeholder}\"\n"
            "      threshold: 30      # TODO: confirm cutoff per guideline\n"
            "      comparator: \"<\"\n"
        )
    elif cat_suffix == "INFECTION-SCREENING":
        trigger_yaml = (
            "trigger:\n"
            "  type: biomarker\n"
            "  any_of:\n"
            f"    - finding: \"{finding_placeholder}\"\n"
            "      value: \"positive\"\n"
        )
    elif cat_suffix == "HIGH-RISK-BIOLOGY":
        trigger_yaml = (
            "trigger:\n"
            "  type: biomarker\n"
            "  any_of:\n"
            f"    - finding: \"{finding_placeholder}\"\n"
            "      value: true\n"
        )
    elif cat_suffix == "TRANSFORMATION-PROGRESSION":
        trigger_yaml = (
            "trigger:\n"
            "  type: composite_clinical\n"
            "  any_of:\n"
            f"    - finding: \"{finding_placeholder}\"\n"
            "      value: true\n"
        )
    else:  # FRAILTY-AGE
        trigger_yaml = (
            "trigger:\n"
            "  type: composite_clinical\n"
            "  any_of:\n"
            f"    - finding: \"{finding_placeholder}\"\n"
            "      threshold: 3       # TODO: confirm cutoff\n"
            "      comparator: \">=\"\n"
        )

    body = f"""id: {rf_id}
definition: "TODO: one-line clinical definition of {cat_suffix} in {disease_label}."
definition_ua: "TODO: одне речення UA-визначення {cat_suffix} для {disease_label}."

{trigger_yaml}
clinical_direction: {direction}

severity: {severity}
priority: 100

relevant_diseases:
  - {disease_id}
# shifts_algorithm intentionally left empty for scaffolds. The clinician-author
# must wire this RF into a specific decision_tree step in {algorithm_id} BEFORE
# clearing draft (spec §4 wiring rule 1). Pre-filling here would create false
# orphan-wiring claims (Phase-1 wiring audit, 2026-04-25).
shifts_algorithm: []

# Sources MUST be replaced with real Source IDs (Tier-1/2). Until then,
# CI emits a warning. SRC-TODO is intentionally invalid so the placeholder
# is loud, not silent.
sources:
  - SRC-TODO

last_reviewed: null
draft: true

notes: >
  SCAFFOLD generated by scripts/scaffold_redflags.py.

  Clinician TODO before clearing draft:
    1. Replace `definition` and `definition_ua` with the disease-specific
       clinical statement.
    2. Replace the trigger placeholder finding ({finding_placeholder!r}) and
       threshold/value with the actual machine-evaluable predicate from
       a cited guideline.
    3. Replace SRC-TODO with >=2 Tier-1/2 source IDs (NCCN, ESMO, ASCO,
       FDA label, or peer-reviewed Phase-3 RCT). Source entities must
       exist in knowledge_base/hosted/content/sources/.
    4. Set `last_reviewed` to the date of clinical review.
    5. Add a step in {algorithm_id}.decision_tree that references this
       RF (otherwise CI flags it as orphan).
    6. Set `draft: false`.

  Category hint: {notes_hint}
"""
    return filename, body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="don't write files, just count")
    ap.add_argument("--force", action="store_true", help="overwrite existing scaffolds")
    args = ap.parse_args()

    written = 0
    skipped = 0
    for disease_id, algorithm_id, short, label in ZERO_COVERAGE_DISEASES:
        for cat_suffix, cat_fp, direction, severity, finding, notes in CATEGORIES:
            filename, body = scaffold_yaml(
                disease_id, algorithm_id, label,
                cat_suffix, cat_fp, direction, severity, finding, notes, short,
            )
            target = RF_DIR / filename
            if target.exists() and not args.force:
                skipped += 1
                continue
            if not args.dry_run:
                target.write_text(body, encoding="utf-8")
            written += 1

    action = "Would write" if args.dry_run else "Wrote"
    print(f"{action} {written} scaffold YAMLs to {RF_DIR}")
    if skipped:
        print(f"  Skipped {skipped} that already exist (use --force to overwrite)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
