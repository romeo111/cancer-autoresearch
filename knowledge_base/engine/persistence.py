"""Patient plan persistence — save / load / list / update_superseded_by.

Files live under `patient_plans/<patient_id>/<plan_id>.json` (gitignored
per CHARTER §9.3 — patient data must NOT enter the public KB).

Storage format = the raw JSON dump of `result.to_dict()` (PlanResult or
DiagnosticPlanResult). One file per plan version. Updates to
superseded_by happen in place (revisions chain stays consistent on
disk).

Hard rule (CHARTER §9.3): this module never writes patient data anywhere
other than the configured root (`patient_plans/` by default). It also
never tries to commit or push — that's caller responsibility, and the
gitignore rule makes accidental commits non-trivial.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from .diagnostic import DiagnosticPlanResult
from .plan import PlanResult


DEFAULT_ROOT = Path("patient_plans")


# ── Internal helpers ──────────────────────────────────────────────────────


def _result_plan_id(result: Union[PlanResult, DiagnosticPlanResult]) -> str:
    if isinstance(result, DiagnosticPlanResult):
        if result.diagnostic_plan is None:
            raise ValueError("DiagnosticPlanResult has no diagnostic_plan; nothing to persist.")
        return result.diagnostic_plan.id
    if result.plan is None:
        raise ValueError("PlanResult has no plan; nothing to persist.")
    return result.plan.id


def _result_patient_id(result: Union[PlanResult, DiagnosticPlanResult]) -> str:
    pid = result.patient_id
    if not pid:
        raise ValueError(
            "Result has no patient_id — required for persistence path "
            "(patient_plans/<patient_id>/<plan_id>.json)."
        )
    return pid


def _path_for(plan_id: str, patient_id: str, root: Path) -> Path:
    return root / patient_id / f"{plan_id}.json"


# ── Public API ────────────────────────────────────────────────────────────


def save_result(
    result: Union[PlanResult, DiagnosticPlanResult],
    root: Path = DEFAULT_ROOT,
) -> Path:
    """Persist a PlanResult or DiagnosticPlanResult to disk. Returns the
    written path. Idempotent: re-saving the same result overwrites."""

    plan_id = _result_plan_id(result)
    patient_id = _result_patient_id(result)
    out_path = _path_for(plan_id, patient_id, root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = result.to_dict()
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return out_path


def load_result(
    path_or_plan_id: Union[Path, str],
    root: Path = DEFAULT_ROOT,
) -> Union[PlanResult, DiagnosticPlanResult]:
    """Load a previously-saved result. Accepts either a file path OR a
    plan id (resolved via patient_plans/*/<plan_id>.json glob)."""

    target: Optional[Path] = None
    if isinstance(path_or_plan_id, Path):
        target = path_or_plan_id
    else:
        as_path = Path(path_or_plan_id)
        if as_path.is_file():
            target = as_path
        else:
            # Treat as a plan id; look it up under root
            matches = sorted(root.glob(f"*/{path_or_plan_id}.json"))
            if not matches:
                raise FileNotFoundError(
                    f"No saved plan with id {path_or_plan_id!r} under {root}."
                )
            if len(matches) > 1:
                raise FileExistsError(
                    f"Multiple saved plans match id {path_or_plan_id!r}: {matches}"
                )
            target = matches[0]

    raw = json.loads(target.read_text(encoding="utf-8"))
    return _reconstruct_result(raw)


def _reconstruct_result(
    raw: dict,
) -> Union[PlanResult, DiagnosticPlanResult]:
    """Rebuild a result dataclass from its serialised dict. Same logic
    used by CLI _load_previous_result; centralised here so revisions
    workflows can rely on it."""

    from knowledge_base.schemas import (
        DiagnosticPlan,
        Plan,
        SuspicionSnapshot,
    )

    if raw.get("diagnostic_plan"):
        dp = DiagnosticPlan.model_validate(raw["diagnostic_plan"])
        susp_raw = raw.get("suspicion")
        susp = SuspicionSnapshot.model_validate(susp_raw) if susp_raw else None
        return DiagnosticPlanResult(
            patient_id=raw.get("patient_id"),
            suspicion=susp,
            diagnostic_plan=dp,
            matched_workup_id=raw.get("matched_workup_id"),
            warnings=list(raw.get("warnings") or []),
        )
    if raw.get("plan"):
        plan = Plan.model_validate(raw["plan"])
        return PlanResult(
            patient_id=raw.get("patient_id"),
            disease_id=raw.get("disease_id"),
            algorithm_id=raw.get("algorithm_id"),
            plan=plan,
            default_indication_id=raw.get("default_indication_id"),
            alternative_indication_id=raw.get("alternative_indication_id"),
            default_indication=raw.get("default_indication"),
            alternative_indication=raw.get("alternative_indication"),
            trace=list(raw.get("trace") or []),
            warnings=list(raw.get("warnings") or []),
        )
    raise ValueError(
        "Saved file has neither `plan` nor `diagnostic_plan` key — "
        "looks like a stale or corrupt persistence record."
    )


def list_versions(patient_id: str, root: Path = DEFAULT_ROOT) -> list[dict]:
    """Return [{plan_id, version, mode, supersedes, superseded_by, path}]
    sorted by version. Empty list if no records."""

    pdir = root / patient_id
    if not pdir.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(pdir.glob("*.json")):
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if raw.get("diagnostic_plan"):
            dp = raw["diagnostic_plan"]
            out.append({
                "plan_id": dp.get("id"),
                "version": dp.get("version", 0),
                "mode": "diagnostic",
                "supersedes": dp.get("supersedes"),
                "superseded_by": dp.get("superseded_by"),
                "path": f,
            })
        elif raw.get("plan"):
            p = raw["plan"]
            out.append({
                "plan_id": p.get("id"),
                "version": p.get("version", 0),
                "mode": "treatment",
                "supersedes": p.get("supersedes"),
                "superseded_by": p.get("superseded_by"),
                "path": f,
            })
    # Stable sort: by mode (diagnostic first), then by version asc
    out.sort(key=lambda r: (0 if r["mode"] == "diagnostic" else 1, r["version"]))
    return out


def update_superseded_by_on_disk(
    plan_id: str,
    new_id: str,
    root: Path = DEFAULT_ROOT,
) -> Path:
    """In-place mutate a saved plan's superseded_by field. Used by
    revisions workflows so the on-disk chain matches what
    revise_plan() produces in memory."""

    matches = sorted(root.glob(f"*/{plan_id}.json"))
    if not matches:
        raise FileNotFoundError(
            f"No saved plan with id {plan_id!r} under {root} to update."
        )
    if len(matches) > 1:
        raise FileExistsError(
            f"Multiple saved plans match id {plan_id!r}: {matches}"
        )
    target = matches[0]
    raw = json.loads(target.read_text(encoding="utf-8"))
    if raw.get("diagnostic_plan"):
        raw["diagnostic_plan"]["superseded_by"] = new_id
    elif raw.get("plan"):
        raw["plan"]["superseded_by"] = new_id
    else:
        raise ValueError(f"{target} has no plan / diagnostic_plan to mutate.")
    target.write_text(
        json.dumps(raw, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return target


def latest_version_path(
    patient_id: str,
    root: Path = DEFAULT_ROOT,
) -> Optional[Path]:
    """Path to the most recent (highest version, treatment > diagnostic)
    saved plan for a patient, or None."""

    versions = list_versions(patient_id, root=root)
    if not versions:
        return None
    return versions[-1]["path"]


__all__ = [
    "DEFAULT_ROOT",
    "latest_version_path",
    "list_versions",
    "load_result",
    "save_result",
    "update_superseded_by_on_disk",
]
