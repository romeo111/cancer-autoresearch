"""CLI: generate a treatment plan for a patient profile JSON.

Usage:
    python -m knowledge_base.engine.cli examples/patient_zero_indolent.json
    python -m knowledge_base.engine.cli patient.json --kb knowledge_base/hosted/content
    python -m knowledge_base.engine.cli patient.json --json-output plan.json --verbose
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

from .plan import generate_plan

# Force UTF-8 stdout so Cyrillic + symbols print correctly on Windows cp1252
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _print_track(t, indent: str = "  ") -> None:
    flag = " * DEFAULT" if t.is_default else ""
    print(f"{indent}[{t.track_id}]{flag}  {t.label} ({t.label_en})")
    print(f"{indent}  Indication: {t.indication_id}")
    if t.regimen_data:
        print(f"{indent}  Regimen:    {t.regimen_data.get('id')} — {t.regimen_data.get('name', '')}")
    if t.supportive_care_data:
        sc = ", ".join(s.get("id", "?") for s in t.supportive_care_data)
        print(f"{indent}  Supportive: {sc}")
    if t.contraindications_data:
        ci = ", ".join(c.get("id", "?") for c in t.contraindications_data)
        print(f"{indent}  Contraindications: {ci}")
    if t.selection_reason:
        print(f"{indent}  Reason: {t.selection_reason[:100]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenOnco rule engine — generate a Plan with multiple tracks.")
    parser.add_argument("patient", type=Path, help="Patient profile JSON")
    parser.add_argument(
        "--kb",
        type=Path,
        default=Path("knowledge_base/hosted/content"),
        help="Path to hosted/content/ root",
    )
    parser.add_argument("--json-output", type=Path, help="Write full Plan JSON here")
    parser.add_argument("--verbose", action="store_true", help="Print trace + warnings + sources")
    args = parser.parse_args()

    if not args.patient.is_file():
        print(f"ERROR: patient file not found: {args.patient}", file=sys.stderr)
        return 2

    patient = json.loads(args.patient.read_text(encoding="utf-8"))
    result = generate_plan(patient, kb_root=args.kb)

    print(f"Patient:   {result.patient_id or '<anonymous>'}")
    print(f"Disease:   {result.disease_id}")
    print(f"Algorithm: {result.algorithm_id}")

    if result.plan:
        print(f"Plan id:   {result.plan.id}  (v{result.plan.version})")
        print()
        print(f"Tracks ({len(result.plan.tracks)}):")
        for t in result.plan.tracks:
            _print_track(t)
            print()

        fda = result.plan.fda_compliance
        print("FDA Criterion 4 metadata (surfaced in rendered document):")
        print(f"  Intended use:   {fda.intended_use}")
        print(f"  HCP user:       {fda.hcp_user_specification[:100]}...")
        print(f"  Population:     {fda.patient_population_match}")
        print(f"  Algorithm:      {fda.algorithm_summary[:100]}...")
        print(f"  Time-critical:  {fda.time_critical}")
        if fda.data_limitations:
            print(f"  Limitations:    {len(fda.data_limitations)} item(s)")
        if args.verbose:
            print(f"  Sources cited:  {len(fda.data_sources_summary)}")
            for s in fda.data_sources_summary:
                print(f"    - {s}")

    if args.verbose:
        print("\nTrace:")
        for entry in result.trace:
            print(f"  {entry}")
        if result.warnings:
            print("\nWarnings:")
            for w in result.warnings:
                print(f"  - {w}")

    if args.json_output:
        args.json_output.write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"\nFull Plan JSON written to {args.json_output}")

    if not result.default_indication_id:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
