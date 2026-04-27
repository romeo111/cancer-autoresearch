"""Coverage + structure checks for critical_field_explanations.yaml.

Guards two things:

1. Every (disease_id, field) marked impact='critical' in any questionnaire
   resolves to either a per-disease override or a base entry. Adding a new
   critical field to a questionnaire without a corresponding explanation
   fails CI here, not silently in production.

2. Each entry has the required shape (short, why, affects).
"""

from __future__ import annotations

from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parent.parent
QDIR = REPO / "knowledge_base" / "hosted" / "content" / "questionnaires"
EXPL = REPO / "knowledge_base" / "hosted" / "content" / "critical_field_explanations.yaml"


def _load_explanations() -> dict:
    return yaml.safe_load(EXPL.read_text(encoding="utf-8")) or {}


def _critical_pairs_in_questionnaires() -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for path in sorted(QDIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        did = data.get("disease_id")
        for group in data.get("groups") or []:
            for q in group.get("questions") or []:
                if q.get("impact") == "critical":
                    pairs.add((did, q.get("field")))
    return pairs


def test_explanations_file_loads_and_has_entries():
    doc = _load_explanations()
    assert "entries" in doc
    assert isinstance(doc["entries"], list)
    assert len(doc["entries"]) > 0


def test_each_entry_has_required_shape():
    doc = _load_explanations()
    for ent in doc["entries"]:
        field = ent.get("field")
        assert field, f"entry missing field: {ent}"
        base = ent.get("base") or {}
        assert base.get("short"), f"{field}: base.short required"
        assert base.get("why"), f"{field}: base.why required"
        affects = base.get("affects") or []
        assert isinstance(affects, list) and len(affects) >= 1, (
            f"{field}: base.affects must be a non-empty list"
        )


def test_every_critical_field_pair_resolves():
    """Coverage gate: each (disease_id, field) flagged impact=critical in a
    questionnaire must resolve to a per_disease override or base entry.
    """
    doc = _load_explanations()
    base_fields = {e["field"] for e in doc["entries"]}
    per_disease: dict[str, set[str]] = {}
    for ent in doc["entries"]:
        for did, _ in (ent.get("per_disease") or {}).items():
            per_disease.setdefault(did, set()).add(ent["field"])

    needed = _critical_pairs_in_questionnaires()
    unresolved = [
        (d, f) for d, f in needed
        if f not in base_fields and f not in per_disease.get(d, set())
    ]
    assert not unresolved, (
        "critical_field_explanations.yaml missing entries for: "
        + ", ".join(f"{d}/{f}" for d, f in sorted(unresolved))
    )


def test_per_disease_overrides_reference_known_fields():
    """An override block must hang off a base entry — a per_disease key
    cannot exist without a sibling base."""
    doc = _load_explanations()
    for ent in doc["entries"]:
        if ent.get("per_disease"):
            assert ent.get("base"), (
                f"{ent.get('field')}: per_disease without base"
            )
