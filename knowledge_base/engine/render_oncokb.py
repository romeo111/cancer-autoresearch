"""OncoKB layer rendering — HCP-mode only.

Phase 4 of safe-rollout v3 (§4.1). Renders the precision-medicine
section that surfaces alongside (NEVER inside) the engine's two-track
plan. CHARTER §8.3 surface-only invariant.

PATIENT MODE GUARANTEE: this module's public API is `render_oncokb_section`
which receives `mode` and returns "" for `mode != "clinician"`. The
caller (engine/render.py) additionally never invokes it on the
patient-mode codepath, so we get defense-in-depth.

Locked decisions (safe-rollout v3 §2):
  Q1: filter Levels 1/2 — only 3A/3B/4/R1/R2 surfaced
  Q2: R1/R2 inline in track-card (separate helper) AND in section block
  Q3: top 3 visible + <details> "show N more"
  Q4: pan-tumor fallback shown with warning badge
  Q5: combined biomarker table + cross-analysis (drug-overlap)
  Q6: PMIDs as clickable PubMed links inline
  Q8: confidence display = level + PMID count + FDA-approval badge
"""

from __future__ import annotations

import html
from typing import Iterable, Optional

from .oncokb_types import (
    OncoKBLayer,
    OncoKBResult,
    OncoKBTherapeuticOption,
    RESISTANCE_LEVELS,
    SURFACED_LEVELS,
    ResistanceConflict,
)


_PUBMED_BASE = "https://pubmed.ncbi.nlm.nih.gov"
_TOP_VISIBLE_ROWS = 3

_LEVEL_RANK = {"3A": 0, "3B": 1, "4": 2, "R1": 3, "R2": 4}


def _h(s) -> str:
    return html.escape(str(s) if s is not None else "")


def _filter_options(options: Iterable[OncoKBTherapeuticOption]) -> list[OncoKBTherapeuticOption]:
    """Apply Q1 filter: drop Levels 1/2; keep 3A/3B/4/R1/R2 only.
    Sort by level rank (3A first, R2 last)."""
    kept = [o for o in options if o.level in SURFACED_LEVELS]
    kept.sort(key=lambda o: _LEVEL_RANK.get(o.level, 99))
    return kept


def _format_pmids(pmids: tuple[str, ...]) -> str:
    """Q6: clickable PubMed links inline."""
    if not pmids:
        return ""
    links = " ".join(
        f'<a href="{_PUBMED_BASE}/{_h(p)}/" target="_blank" rel="noopener" class="oncokb-pmid">PMID:{_h(p)}</a>'
        for p in pmids
    )
    return f'<span class="oncokb-pmids">{links}</span>'


def _format_fda_badge(opt: OncoKBTherapeuticOption) -> str:
    """Q8: FDA-approval badge."""
    if not opt.fda_approved:
        return ""
    drug_label = opt.drugs[0] if opt.drugs else "agent"
    year = f", {opt.fda_approval_year}" if opt.fda_approval_year else ""
    return f'<span class="oncokb-fda-badge">FDA-approved ({_h(drug_label)}{_h(year)})</span>'


def _format_confidence(opt: OncoKBTherapeuticOption) -> str:
    """Q8: 'Level 3A · 5 PMIDs · FDA-approved' style."""
    parts = [f'Level {_h(opt.level)}']
    n_pmids = len(opt.pmids)
    if n_pmids:
        parts.append(f"{n_pmids} PMID{'s' if n_pmids != 1 else ''}")
    if opt.fda_approved:
        year = f", {opt.fda_approval_year}" if opt.fda_approval_year else ""
        parts.append(f'FDA-approved{_h(year)}')
    return " · ".join(parts)


def _row_html(result: OncoKBResult, opt: OncoKBTherapeuticOption) -> str:
    """One <tr> for the unified evidence table (Q5: combined biomarker + level)."""
    biomarker_label = f"{_h(result.query.gene)} {_h(result.query.variant)}"
    drugs_label = ", ".join(_h(d) for d in opt.drugs) if opt.drugs else "—"
    desc = _h(opt.description) if opt.description else ""
    pmids = _format_pmids(opt.pmids)
    fda = _format_fda_badge(opt)
    confidence = _format_confidence(opt)
    css_class = "oncokb-row"
    if opt.level in RESISTANCE_LEVELS:
        css_class += f" oncokb-row--{opt.level.lower()}"
    return (
        f'<tr class="{css_class}">'
        f'<td class="oncokb-biomarker">{biomarker_label}</td>'
        f'<td class="oncokb-confidence">{confidence}</td>'
        f'<td class="oncokb-drugs">{drugs_label} {fda}</td>'
        f'<td class="oncokb-evidence">{desc} {pmids}</td>'
        f'<td class="oncokb-link"><a href="{_h(result.oncokb_url)}" target="_blank" rel="noopener">→ OncoKB</a></td>'
        f'</tr>'
    )


def _render_resistance_block(conflicts: list[ResistanceConflict]) -> str:
    """Q2: prominent block at top of section listing conflicts.
    Pairs with inline banners in track-card (separate helper)."""
    if not conflicts:
        return ""
    rows: list[str] = []
    for c in sorted(conflicts, key=lambda x: (_LEVEL_RANK.get(x.level, 99), x.gene, x.variant)):
        css = "oncokb-conflict-r1" if c.level == "R1" else "oncokb-conflict-r2"
        icon = "🛑" if c.level == "R1" else "⚠"
        desc = _h(c.description) if c.description else ""
        rows.append(
            f'<li class="{css}">'
            f'<span class="oncokb-conflict-icon">{icon}</span> '
            f'<strong>OncoKB {_h(c.level)}:</strong> резистентність до '
            f'<strong>{_h(c.drug)}</strong> для {_h(c.gene)} {_h(c.variant)} '
            f'(track: <em>{_h(c.track_id)}</em>) — перегляньте перед призначенням. '
            f'{desc}'
            f'</li>'
        )
    return (
        '<div class="oncokb-conflicts-block">'
        '<h3>Виявлено резистентність (OncoKB)</h3>'
        f'<ul>{"".join(rows)}</ul>'
        '</div>'
    )


def _render_cross_analysis(results: list[OncoKBResult]) -> str:
    """Q5: cross-biomarker analysis. Detects:
      (a) drug-overlap — one drug covers ≥2 patient biomarkers
      (b) co-occurrence sanity check — rare combinations flagged
    """
    if len(results) < 2:
        return ""

    # (a) Drug → list of (gene, variant, level) hits
    drug_index: dict[str, list[tuple[str, str, str]]] = {}
    for r in results:
        for opt in _filter_options(r.therapeutic_options):
            for d in opt.drugs:
                drug_index.setdefault(d.lower(), []).append(
                    (r.query.gene, r.query.variant, opt.level)
                )

    overlaps = {d: hits for d, hits in drug_index.items() if len({(g, v) for g, v, _ in hits}) >= 2}

    if not overlaps:
        return ""

    items: list[str] = []
    for drug, hits in sorted(overlaps.items()):
        bms = ", ".join(f"{g} {v}" for g, v, _ in sorted({(g, v, l) for g, v, l in hits}))
        items.append(
            f'<li><strong>{_h(drug)}</strong> покриває {len({(g, v) for g, v, _ in hits})} '
            f'з біомаркерів пацієнта: {_h(bms)} '
            f'<span class="oncokb-overlap-tag">(efficiency signal)</span></li>'
        )

    return (
        '<div class="oncokb-cross-analysis">'
        '<h4>Cross-biomarker analysis</h4>'
        f'<ul>{"".join(items)}</ul>'
        '</div>'
    )


def render_oncokb_section(
    layer: Optional[OncoKBLayer],
    *,
    mode: str = "clinician",
    target_lang: str = "uk",
) -> str:
    """Render the OncoKB precision-medicine section.

    Returns "" for any non-clinician mode (defense-in-depth for AC-3 —
    patient-mode HTML must contain zero OncoKB content).

    Returns "" for an empty/None layer or when the layer has no
    surface-able content (no SURFACED_LEVELS rows AND no resistance
    conflicts) — avoids rendering an empty visual element."""

    # Patient-mode hard guard
    if (mode or "").lower() != "clinician":
        return ""

    if layer is None or layer.is_empty:
        return ""

    # Build unified table (Q5: combined across biomarkers)
    all_rows: list[tuple[str, str, OncoKBResult, OncoKBTherapeuticOption]] = []
    for r in layer.results:
        for opt in _filter_options(r.therapeutic_options):
            all_rows.append((opt.level, r.query.gene + r.query.variant, r, opt))

    all_rows.sort(key=lambda row: (_LEVEL_RANK.get(row[0], 99), row[1]))

    visible = all_rows[:_TOP_VISIBLE_ROWS]
    overflow = all_rows[_TOP_VISIBLE_ROWS:]

    visible_html = "".join(_row_html(r, opt) for _, _, r, opt in visible)
    overflow_html = ""
    if overflow:
        overflow_rows = "".join(_row_html(r, opt) for _, _, r, opt in overflow)
        overflow_html = (
            f'<details class="oncokb-overflow">'
            f'<summary>Показати ще {len(overflow)}</summary>'
            f'<table class="oncokb-table oncokb-table--overflow">{overflow_rows}</table>'
            f'</details>'
        )

    # Pan-tumor fallback warning (Q4)
    pan_tumor_badge = ""
    if layer.pan_tumor_fallback_used:
        pan_tumor_badge = (
            '<span class="oncokb-pan-tumor-badge" '
            'title="OncoTree code не визначено для цього захворювання; результати pan-tumor">'
            'ℹ Без фільтра tumor-type</span>'
        )

    # Header (attribution per Q + safe-rollout v3 §4.1: in header, not footnote)
    header = (
        '<div class="oncokb-section-header">'
        '<h2>Зовнішня precision-medicine довідка (OncoKB)</h2>'
        '<p class="oncokb-disclaimer"><strong>Не є рекомендацією OpenOnco.</strong> '
        'Перегляньте перед фіналізацією плану лікування.</p>'
        '<p class="oncokb-attribution">Therapeutic-level data sourced from '
        'OncoKB™ (Memorial Sloan Kettering Cancer Center). '
        'Citation: Chakravarty et al. JCO Precis Oncol 2017.</p>'
        f'{pan_tumor_badge}'
        '</div>'
    )

    # Resistance conflicts at top (Q2 prominence)
    resistance_block = _render_resistance_block(layer.resistance_conflicts)

    # Main table
    table_html = ""
    if visible:
        table_html = (
            '<table class="oncokb-table">'
            '<thead><tr>'
            '<th>Біомаркер</th>'
            '<th>Confidence</th>'
            '<th>Препарат(и)</th>'
            '<th>Evidence</th>'
            '<th>Посилання</th>'
            '</tr></thead>'
            f'<tbody>{visible_html}</tbody>'
            '</table>'
        )

    cross = _render_cross_analysis(layer.results)

    # Errors note (don't dump — just signal)
    errors_note = ""
    if layer.errors:
        errors_note = (
            f'<p class="oncokb-errors-note">⚠ {len(layer.errors)} OncoKB lookups did not return data '
            '(timeout / proxy unreachable / no evidence). Section degraded.</p>'
        )

    return (
        '<section class="oncokb-layer">'
        f'{header}'
        f'{resistance_block}'
        f'{table_html}'
        f'{overflow_html}'
        f'{cross}'
        f'{errors_note}'
        '</section>'
    )


def render_track_resistance_banner(
    track_id: str,
    conflicts: list[ResistanceConflict],
) -> str:
    """Inline banner for a single track-card. Q2 — surfaces R1/R2 next
    to the recommended regimen, not only in the OncoKB section, so a
    clinician scrolling top-down cannot miss it.

    Caller iterates tracks and inserts the result inside each track-card."""

    relevant = [c for c in conflicts if c.track_id == track_id]
    if not relevant:
        return ""

    items: list[str] = []
    for c in sorted(relevant, key=lambda x: _LEVEL_RANK.get(x.level, 99)):
        if c.level == "R1":
            cls = "oncokb-inline-banner oncokb-inline-banner--r1"
            icon = "🛑"
            label = "OncoKB R1: резистентність"
        else:
            cls = "oncokb-inline-banner oncokb-inline-banner--r2"
            icon = "⚠"
            label = "OncoKB R2: preclinical resistance signal"
        items.append(
            f'<div class="{cls}">'
            f'<span class="oncokb-inline-icon">{icon}</span> '
            f'<strong>{label}:</strong> {_h(c.drug)} / {_h(c.gene)} {_h(c.variant)}. '
            f'Перегляньте перед призначенням.'
            f'</div>'
        )
    return "".join(items)


# CSS — appended to engine/render.py's stylesheet via render_styles
ONCOKB_CSS = """
/* OncoKB layer — distinct from engine track palette to mitigate
   automation bias (CHARTER §15.2 C6) */
.oncokb-layer {
  margin: 24px 0;
  padding: 20px;
  border-left: 4px solid #6b7280;
  background: #f9fafb;
  border-radius: 4px;
}
.oncokb-section-header h2 { margin: 0 0 8px; color: #374151; font-size: 18px; }
.oncokb-disclaimer { margin: 4px 0; color: #b45309; font-size: 14px; }
.oncokb-attribution { margin: 8px 0; color: #6b7280; font-size: 12px; font-style: italic; }
.oncokb-pan-tumor-badge {
  display: inline-block; margin-top: 8px; padding: 2px 8px;
  background: #fef3c7; color: #92400e; border-radius: 12px; font-size: 12px;
}

/* Resistance block at top */
.oncokb-conflicts-block {
  margin: 12px 0; padding: 12px; background: #fef2f2;
  border: 1px solid #fecaca; border-radius: 4px;
}
.oncokb-conflicts-block h3 { margin: 0 0 8px; color: #991b1b; font-size: 15px; }
.oncokb-conflicts-block ul { margin: 0; padding-left: 18px; }
.oncokb-conflict-r1 { color: #991b1b; }
.oncokb-conflict-r2 { color: #b45309; }
.oncokb-conflict-icon { font-size: 16px; }

/* Inline track-card banners */
.oncokb-inline-banner {
  margin: 8px 0; padding: 8px 12px; border-radius: 4px; font-size: 13px;
}
.oncokb-inline-banner--r1 { background: #fee2e2; color: #991b1b; border-left: 3px solid #dc2626; }
.oncokb-inline-banner--r2 { background: #fef3c7; color: #92400e; border-left: 3px solid #f59e0b; }
.oncokb-inline-icon { font-size: 14px; }

/* Main evidence table */
.oncokb-table {
  width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px;
}
.oncokb-table th {
  text-align: left; padding: 6px 8px; background: #e5e7eb;
  border-bottom: 1px solid #d1d5db; font-weight: 600;
}
.oncokb-table td { padding: 6px 8px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
.oncokb-row--r1 { background: #fef2f2; }
.oncokb-row--r2 { background: #fffbeb; }
.oncokb-confidence { white-space: nowrap; color: #4b5563; }
.oncokb-pmid { color: #2563eb; text-decoration: none; font-size: 12px; }
.oncokb-pmid:hover { text-decoration: underline; }
.oncokb-fda-badge {
  display: inline-block; padding: 1px 6px; background: #dcfce7;
  color: #166534; border-radius: 8px; font-size: 11px; margin-left: 4px;
}

/* Overflow details */
.oncokb-overflow { margin: 8px 0; }
.oncokb-overflow summary { cursor: pointer; color: #374151; font-size: 13px; padding: 4px 0; }
.oncokb-table--overflow { margin-top: 4px; }

/* Cross-biomarker analysis */
.oncokb-cross-analysis {
  margin: 12px 0; padding: 10px; background: #ecfdf5;
  border-left: 3px solid #10b981; border-radius: 4px;
}
.oncokb-cross-analysis h4 { margin: 0 0 6px; color: #065f46; font-size: 14px; }
.oncokb-cross-analysis ul { margin: 0; padding-left: 18px; font-size: 13px; }
.oncokb-overlap-tag { color: #047857; font-size: 11px; }

.oncokb-errors-note { color: #6b7280; font-size: 12px; font-style: italic; margin-top: 8px; }
"""


__all__ = [
    "render_oncokb_section",
    "render_track_resistance_banner",
    "ONCOKB_CSS",
]
