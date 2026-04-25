"""Tests for the HTML render layer.

Verifies:
1. Treatment Plan render — well-formed HTML, contains expected sections
2. Diagnostic Brief render — diagnostic banner mandatory + workup steps + mandatory questions visible
3. Revision Note render — transition + previous/new IDs + inline new content
4. Embedded CSS only (single-file output, no external <link> for CSS)
5. FDA disclosure present in every output
6. Cyrillic content renders without encoding issues
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from knowledge_base.engine import (
    generate_diagnostic_brief,
    generate_plan,
    orchestrate_mdt,
    render_diagnostic_brief_html,
    render_plan_html,
    render_revision_note_html,
    revise_plan,
)

REPO_ROOT = Path(__file__).parent.parent
KB_ROOT = REPO_ROOT / "knowledge_base" / "hosted" / "content"
EXAMPLES = REPO_ROOT / "examples"


def _patient(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


# ── Treatment plan render ─────────────────────────────────────────────────


def test_treatment_plan_html_well_formed():
    p = _patient("patient_zero_indolent.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    mdt = orchestrate_mdt(p, plan, kb_root=KB_ROOT)
    html = render_plan_html(plan, mdt=mdt)

    assert html.startswith("<!DOCTYPE html>")
    assert "<html lang=\"uk\">" in html
    assert "<title>" in html and "</title>" in html
    assert "</body>" in html and "</html>" in html
    # CSS embedded, not external (single-file output)
    assert "<style>" in html
    # No external CSS link references (only Google Fonts is allowed)
    css_links = re.findall(r'<link[^>]*rel="stylesheet"[^>]*>', html)
    for link in css_links:
        assert "fonts.googleapis.com" in link, (
            f"non-fonts external CSS link found: {link}"
        )


def test_treatment_plan_shows_both_tracks():
    p = _patient("patient_zero_indolent.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    html = render_plan_html(plan, mdt=None)

    assert plan.default_indication_id in html
    assert plan.alternative_indication_id in html
    # Default badge visible somewhere
    assert "DEFAULT" in html or "★" in html


def test_treatment_plan_includes_fda_disclosure():
    p = _patient("patient_zero_indolent.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    html = render_plan_html(plan, mdt=None)
    assert "fda-disclosure" in html
    assert "CHARTER §15" in html
    assert "medical-disclaimer" in html


def test_treatment_plan_renders_mdt_when_provided():
    p = _patient("patient_zero_indolent.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    mdt = orchestrate_mdt(p, plan, kb_root=KB_ROOT)
    html = render_plan_html(plan, mdt=mdt)
    assert "MDT brief" in html
    assert "hematologist" in html or "Гематолог" in html


# ── Diagnostic brief render ───────────────────────────────────────────────


def test_diagnostic_brief_html_contains_mandatory_banner():
    """CHARTER §15.2 C7 — diagnostic banner must be visible above the fold."""
    p = _patient("patient_diagnostic_lymphoma_suspect.json")
    diag = generate_diagnostic_brief(p, kb_root=KB_ROOT)
    html = render_diagnostic_brief_html(diag, mdt=None)
    assert "DIAGNOSTIC PHASE" in html
    assert "TREATMENT PLAN NOT YET APPLICABLE" in html
    assert "banner--diagnostic" in html


def test_diagnostic_brief_shows_workup_steps_and_questions():
    p = _patient("patient_diagnostic_lymphoma_suspect.json")
    diag = generate_diagnostic_brief(p, kb_root=KB_ROOT)
    html = render_diagnostic_brief_html(diag, mdt=None)

    # Workup steps section
    assert "Workup steps" in html
    # IHC + biopsy described inline
    assert "CD20" in html  # IHC baseline marker
    # Mandatory questions section visible
    assert "Питання що мають бути закриті" in html


def test_diagnostic_brief_has_matched_workup_in_output():
    p = _patient("patient_diagnostic_lymphoma_suspect.json")
    diag = generate_diagnostic_brief(p, kb_root=KB_ROOT)
    html = render_diagnostic_brief_html(diag, mdt=None)
    assert "WORKUP-SUSPECTED-LYMPHOMA" in html


# ── Revision note render ─────────────────────────────────────────────────


def test_revision_note_shows_transition_and_ids():
    susp = _patient("patient_diagnostic_lymphoma_suspect.json")
    confirmed = _patient("patient_diagnostic_lymphoma_confirmed.json")

    diag_v1 = generate_diagnostic_brief(susp, kb_root=KB_ROOT)
    revised_prev, plan_v1 = revise_plan(
        confirmed, diag_v1, "biopsy 2026-05-10: HCV-MZL confirmed", kb_root=KB_ROOT,
    )
    html = render_revision_note_html(revised_prev, plan_v1, "diagnostic→treatment", mdt=None)

    assert "Revision Note" in html
    assert "diagnostic→treatment" in html
    assert diag_v1.diagnostic_plan.id in html
    assert plan_v1.plan.id in html
    # Trigger surfaced
    assert "biopsy 2026-05-10" in html


# ── Cyrillic / unicode safety ─────────────────────────────────────────────


def test_cyrillic_content_renders_without_loss():
    p = _patient("patient_diagnostic_lymphoma_suspect.json")
    diag = generate_diagnostic_brief(p, kb_root=KB_ROOT)
    html = render_diagnostic_brief_html(diag, mdt=None)
    # The mandatory_questions text is in Ukrainian — must be preserved intact
    assert "лімфома" in html.lower() or "лімфому" in html.lower()
    # Encoding declared
    assert 'charset="UTF-8"' in html


# ── No patient PII leaked from the reference HTML files ──────────────────


def test_render_does_not_leak_reference_patient_initials():
    """The infograph reference HTML files contain real patient initials
    (V.D.V.). We borrow only the visual idiom, never the patient text.
    Smoke check that the rendered output of a synthetic patient contains
    no string that looks like the reference patient ID."""
    p = _patient("patient_zero_indolent.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    html = render_plan_html(plan, mdt=None)
    # Latin and Cyrillic forms of the reference patient initials
    assert "V.D.V" not in html
    assert "В.Д.В" not in html


# ── Skill version metadata in MDT brief (per user request) ────────────────


def test_mdt_brief_shows_skill_version_per_role():
    """Each activated role in the rendered MDT brief must show the skill's
    version + last_reviewed date inline so a clinician verifying changes
    can see at a glance which version produced that activation."""
    p = _patient("patient_zero_indolent.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    mdt = orchestrate_mdt(p, plan, kb_root=KB_ROOT)
    html = render_plan_html(plan, mdt=mdt)

    # Skill metadata strip class must be present
    assert "skill-meta" in html
    # At least one version pill rendered (e.g., "v0.1.0")
    import re
    assert re.search(r"v\d+\.\d+\.\d+", html), "no semver version pill in rendered HTML"
    # last_reviewed date format (e.g., "reviewed 2026-04-25")
    assert "reviewed " in html
    # STUB or REVIEWED status pill
    assert ("STUB" in html) or ("REVIEWED" in html)


def test_mdt_brief_includes_skill_catalog_with_activation_markers():
    """Skill catalog footer must list ALL registered skills with their
    versions, so a clinician can see which dormant skills are available
    for other clinical scenarios."""
    p = _patient("patient_zero_indolent.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    mdt = orchestrate_mdt(p, plan, kb_root=KB_ROOT)
    html = render_plan_html(plan, mdt=mdt)

    assert "skill-catalog" in html
    assert "Skill catalog" in html
    # Every catalog row carries a version
    from knowledge_base.engine.mdt_orchestrator import _SKILL_REGISTRY
    for sid, s in _SKILL_REGISTRY.items():
        assert sid in html, f"skill_id '{sid}' missing from rendered catalog"
    # Activation marker must mention the count
    import re
    m = re.search(r"Skill catalog \((\d+)/(\d+)", html)
    assert m, "skill catalog header missing activation count"
    activated, total = int(m.group(1)), int(m.group(2))
    assert total == len(_SKILL_REGISTRY)
    assert 1 <= activated <= total


def test_role_block_uses_skill_framing_in_ukrainian():
    """User explicitly requested 'віртуальні спеціалісти' framing instead
    of generic 'roles'."""
    p = _patient("patient_zero_indolent.json")
    plan = generate_plan(p, kb_root=KB_ROOT)
    mdt = orchestrate_mdt(p, plan, kb_root=KB_ROOT)
    html = render_plan_html(plan, mdt=mdt)
    assert "Скіли" in html or "віртуальні спеціалісти" in html.lower()
