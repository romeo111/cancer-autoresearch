"""Skeleton generator for golden RedFlag test fixtures (Phase 5).

For each non-draft RedFlag, produces a directory:

    tests/fixtures/redflags/<rf_id>/
        positive.yaml   # findings that satisfy the trigger
        negative.yaml   # findings that don't satisfy the trigger

Fixture format (matches existing tests/test_redflag_fixtures.py contract):

    red_flag: RF-FOO
    findings:
        some_finding_key: <value>
    expected_fires: true | false

Skeletons are derived mechanically from `trigger.any_of` / `trigger.all_of`
clauses: positive flips every clause to satisfaction; negative flips them
to non-satisfaction.

This script is idempotent: it never overwrites a hand-curated fixture.
A fixture file that already exists is skipped, and a NOTE is printed.

Usage:
    python scripts/generate_redflag_fixtures.py
    python scripts/generate_redflag_fixtures.py --dry-run
    python scripts/generate_redflag_fixtures.py --filter RF-DLBCL
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
KB_REDFLAGS = REPO_ROOT / "knowledge_base" / "hosted" / "content" / "redflags"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "redflags"


def _yaml_load(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _flip_clause(clause: dict, fire: bool) -> dict:
    if "all_of" in clause or "any_of" in clause:
        sub = clause.get("all_of") or clause.get("any_of")
        out: dict[str, Any] = {}
        for c in sub or []:
            out.update(_flip_clause(c, fire))
        return out

    finding = clause.get("finding") or clause.get("condition")
    if not finding:
        return {}

    if "threshold" in clause:
        comp = clause.get("comparator", ">=")
        thr = clause["threshold"]
        if comp == ">=":
            return {finding: (thr if fire else thr - 1)}
        if comp == ">":
            return {finding: (thr + 1 if fire else thr)}
        if comp == "<=":
            return {finding: (thr if fire else thr + 1)}
        if comp == "<":
            return {finding: (thr - 1 if fire else thr)}
        if comp == "==":
            return {finding: (thr if fire else thr + 1)}
        if comp == "!=":
            return {finding: (thr + 1 if fire else thr)}
        return {finding: thr}

    if "value" in clause:
        v = clause["value"]
        if isinstance(v, bool):
            return {finding: v if fire else not v}
        if isinstance(v, str):
            return {finding: v if fire else f"_NOT_{v}"}
        return {finding: v}

    return {finding: True if fire else False}


def _generate_findings(trigger: dict, fire: bool) -> dict:
    out: dict[str, Any] = {}

    if "all_of" in trigger:
        for c in trigger["all_of"]:
            out.update(_flip_clause(c, fire))

    if "any_of" in trigger:
        if fire:
            first = trigger["any_of"][0] if trigger["any_of"] else {}
            out.update(_flip_clause(first, True))
        else:
            for c in trigger["any_of"]:
                out.update(_flip_clause(c, False))

    if "none_of" in trigger:
        for c in trigger["none_of"]:
            out.update(_flip_clause(c, not fire))

    if not out and "finding" in trigger:
        out.update(_flip_clause(trigger, fire))

    return out


def _fixture_yaml(rf_id: str, findings: dict, fires: bool) -> str:
    payload = {
        "red_flag": rf_id,
        "findings": findings,
        "expected_fires": fires,
        "_skeleton": True,
        "_clinician_todo": (
            "Auto-generated from trigger clauses. Inspect findings — for "
            "complex triggers (nested any_of, threshold edge-cases) the "
            "skeleton may be over-permissive. Edit and remove _skeleton "
            "marker once verified."
        ),
    }
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--filter", default="")
    parser.add_argument("--include-drafts", action="store_true")
    args = parser.parse_args()

    written = 0
    skipped_existing = 0
    skipped_drafts = 0

    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)

    for path in sorted(KB_REDFLAGS.rglob("*.yaml")):
        rf = _yaml_load(path)
        if not rf.get("id"):
            continue
        if args.filter and args.filter not in rf["id"]:
            continue
        if rf.get("draft") and not args.include_drafts:
            skipped_drafts += 1
            continue

        rf_dir = FIXTURE_ROOT / rf["id"]
        rf_dir.mkdir(parents=True, exist_ok=True)

        trigger = rf.get("trigger") or {}
        targets = {
            "positive.yaml": _fixture_yaml(rf["id"], _generate_findings(trigger, True), True),
            "negative.yaml": _fixture_yaml(rf["id"], _generate_findings(trigger, False), False),
        }

        for fname, content in targets.items():
            out_path = rf_dir / fname
            if out_path.exists():
                skipped_existing += 1
                continue
            if args.dry_run:
                written += 1
                continue
            out_path.write_text(content, encoding="utf-8")
            written += 1

    print(f"Skeletons written: {written}")
    print(f"Existing files preserved: {skipped_existing}")
    print(f"Draft RFs skipped: {skipped_drafts}")
    if args.dry_run:
        print("(dry-run — no files actually created)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
