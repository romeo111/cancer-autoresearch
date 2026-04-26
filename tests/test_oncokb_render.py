"""OncoKB render tests — Phase 4 of safe-rollout v3.

Covers AC-3, AC-8, AC-16, AC-17, AC-19, AC-20.
"""

from __future__ import annotations

import re

from knowledge_base.engine.oncokb_types import (
    OncoKBLayer,
    OncoKBQuery,
    OncoKBResult,
    OncoKBTherapeuticOption,
    ResistanceConflict,
)
from knowledge_base.engine.render_oncokb import (
    render_oncokb_section,
    render_track_resistance_banner,
)


def _make_result(gene: str, variant: str, options: list[dict]) -> OncoKBResult:
    return OncoKBResult(
        query=OncoKBQuery(gene=gene, variant=variant, oncotree_code=None, source_biomarker_id=f"BIO-{gene}-{variant}"),
        oncokb_url=f"https://www.oncokb.org/gene/{gene}/{variant}",
        therapeutic_options=tuple(
            OncoKBTherapeuticOption(
                level=str(o.get("level", "?")),
                drugs=tuple(o.get("drugs", [])),
                description=o.get("description"),
                pmids=tuple(o.get("pmids", [])),
                fda_approved=bool(o.get("fda_approved", False)),
                fda_approval_year=o.get("fda_approval_year"),
            )
            for o in options
        ),
        cached=False,
    )


# ── AC-3: Patient mode never contains OncoKB content ────────────────────


def test_patient_mode_returns_empty_string():
    layer = OncoKBLayer(
        results=[
            _make_result("BRAF", "V600E", [{"level": "3A", "drugs": ["vemurafenib"]}])
        ]
    )
    out = render_oncokb_section(layer, mode="patient")
    assert out == ""


def test_unknown_mode_returns_empty_string():
    """Defense-in-depth: anything not 'clinician' returns empty."""
    layer = OncoKBLayer(
        results=[_make_result("BRAF", "V600E", [{"level": "3A", "drugs": ["x"]}])]
    )
    for mode in ("guest", "anonymous", "", None, "clinician_lite"):
        out = render_oncokb_section(layer, mode=mode if mode is not None else "")
        assert "oncokb" not in out.lower(), f"mode={mode!r} leaked oncokb content"


def test_patient_mode_regex_grep_no_oncokb_substring():
    """Hard CI-style grep: 'oncokb' must not appear in patient-mode output."""
    layer = OncoKBLayer(
        results=[_make_result("BRAF", "V600E", [{"level": "3A", "drugs": ["x"], "pmids": ["123"]}])],
        resistance_conflicts=[
            ResistanceConflict(
                track_id="standard", drug="gefitinib", gene="EGFR",
                variant="T790M", level="R1", description="resistance",
            )
        ],
    )
    out = render_oncokb_section(layer, mode="patient")
    assert not re.search(r"oncokb", out, re.IGNORECASE)
    assert "vemurafenib" not in out.lower()


# ── AC-16 (Q1): Levels 1/2 filtered out ─────────────────────────────────


def test_levels_1_and_2_never_appear_in_section():
    layer = OncoKBLayer(
        results=[
            _make_result(
                "BRAF", "V600E",
                [
                    {"level": "1", "drugs": ["vemurafenib"], "pmids": ["111"]},
                    {"level": "2", "drugs": ["dabrafenib"], "pmids": ["222"]},
                    {"level": "3A", "drugs": ["encorafenib"], "pmids": ["333"]},
                ],
            )
        ]
    )
    out = render_oncokb_section(layer, mode="clinician")
    assert "Level 3A" in out
    assert "Level 1" not in out
    assert "Level 2" not in out
    # Drug names from filtered-out rows must also not appear
    assert "vemurafenib" not in out.lower()
    assert "dabrafenib" not in out.lower()
    assert "encorafenib" in out.lower()


def test_section_skipped_when_only_levels_1_2_present():
    """If a query returns only Levels 1/2, the section is empty (is_empty=True)."""
    layer = OncoKBLayer(
        results=[
            _make_result(
                "BRAF", "V600E",
                [{"level": "1", "drugs": ["vemurafenib"], "pmids": []}],
            )
        ]
    )
    assert layer.is_empty is True
    assert render_oncokb_section(layer, mode="clinician") == ""


# ── AC-19 (Q6): PMID clickable PubMed links ─────────────────────────────


def test_pmid_renders_as_clickable_pubmed_link():
    layer = OncoKBLayer(
        results=[
            _make_result(
                "EGFR", "T790M",
                [{"level": "3A", "drugs": ["osimertinib"], "pmids": ["29151359"]}],
            )
        ]
    )
    out = render_oncokb_section(layer, mode="clinician")
    assert 'href="https://pubmed.ncbi.nlm.nih.gov/29151359/"' in out
    assert 'target="_blank"' in out
    assert 'rel="noopener"' in out
    assert "PMID:29151359" in out


# ── AC-20 (Q8): FDA-approval badge ──────────────────────────────────────


def test_fda_approval_badge_renders_with_year():
    layer = OncoKBLayer(
        results=[
            _make_result(
                "KRAS", "G12C",
                [{
                    "level": "3A", "drugs": ["sotorasib"],
                    "fda_approved": True, "fda_approval_year": 2021,
                }],
            )
        ]
    )
    out = render_oncokb_section(layer, mode="clinician")
    assert "FDA-approved" in out
    assert "2021" in out
    assert "sotorasib" in out


def test_fda_approval_badge_absent_when_not_approved():
    layer = OncoKBLayer(
        results=[
            _make_result(
                "TP53", "R175H",
                [{"level": "4", "drugs": ["arsenic trioxide"], "fda_approved": False}],
            )
        ]
    )
    out = render_oncokb_section(layer, mode="clinician")
    assert "FDA-approved" not in out


# ── AC-8: Attribution in header, not footnote ───────────────────────────


def test_attribution_in_header_block():
    layer = OncoKBLayer(
        results=[_make_result("BRAF", "V600E", [{"level": "3A", "drugs": ["x"]}])]
    )
    out = render_oncokb_section(layer, mode="clinician")
    # Attribution string present
    assert "Memorial Sloan Kettering" in out
    assert "Chakravarty et al." in out
    # And appears BEFORE the table (header position, not footer)
    attr_idx = out.find("Memorial Sloan Kettering")
    table_idx = out.find("<table")
    assert attr_idx > 0 and table_idx > 0 and attr_idx < table_idx


# ── AC-17 (Q5): Cross-biomarker drug-overlap analysis ───────────────────


def test_cross_analysis_detects_drug_covering_two_biomarkers():
    """One drug appears in ≥2 biomarker rows → overlap detected."""
    layer = OncoKBLayer(
        results=[
            _make_result("EGFR", "L858R", [{"level": "3A", "drugs": ["osimertinib"]}]),
            _make_result("EGFR", "T790M", [{"level": "3A", "drugs": ["osimertinib"]}]),
        ]
    )
    out = render_oncokb_section(layer, mode="clinician")
    assert "Cross-biomarker analysis" in out
    assert "osimertinib" in out.lower()
    assert "efficiency signal" in out


def test_cross_analysis_absent_with_single_biomarker():
    layer = OncoKBLayer(
        results=[_make_result("BRAF", "V600E", [{"level": "3A", "drugs": ["vemurafenib"]}])]
    )
    out = render_oncokb_section(layer, mode="clinician")
    assert "Cross-biomarker analysis" not in out


def test_cross_analysis_absent_when_no_drug_overlap():
    layer = OncoKBLayer(
        results=[
            _make_result("BRAF", "V600E", [{"level": "3A", "drugs": ["vemurafenib"]}]),
            _make_result("KRAS", "G12C", [{"level": "3A", "drugs": ["sotorasib"]}]),
        ]
    )
    out = render_oncokb_section(layer, mode="clinician")
    assert "Cross-biomarker analysis" not in out


# ── Q3: top 3 + show-more collapsible ───────────────────────────────────


def test_top_3_visible_rest_in_details():
    options = [
        {"level": "3A", "drugs": [f"drug-{i}"]}
        for i in range(5)
    ]
    layer = OncoKBLayer(
        results=[_make_result("BRAF", "V600E", options)]
    )
    out = render_oncokb_section(layer, mode="clinician")
    assert "<details" in out
    assert "Показати ще 2" in out


def test_no_details_block_when_3_or_fewer_rows():
    options = [
        {"level": "3A", "drugs": [f"drug-{i}"]}
        for i in range(3)
    ]
    layer = OncoKBLayer(
        results=[_make_result("BRAF", "V600E", options)]
    )
    out = render_oncokb_section(layer, mode="clinician")
    assert "<details" not in out


# ── Q4: Pan-tumor fallback warning badge ────────────────────────────────


def test_pan_tumor_fallback_renders_warning_badge():
    layer = OncoKBLayer(
        results=[_make_result("BRAF", "V600E", [{"level": "3A", "drugs": ["x"]}])],
        pan_tumor_fallback_used=True,
    )
    out = render_oncokb_section(layer, mode="clinician")
    assert "Без фільтра tumor-type" in out


def test_no_pan_tumor_badge_when_oncotree_resolved():
    layer = OncoKBLayer(
        results=[_make_result("BRAF", "V600E", [{"level": "3A", "drugs": ["x"]}])],
        pan_tumor_fallback_used=False,
    )
    out = render_oncokb_section(layer, mode="clinician")
    assert "Без фільтра tumor-type" not in out


# ── Q2: Resistance conflicts inline + section ───────────────────────────


def test_resistance_conflicts_block_at_top_of_section():
    layer = OncoKBLayer(
        results=[],
        resistance_conflicts=[
            ResistanceConflict(
                track_id="standard", drug="gefitinib", gene="EGFR",
                variant="T790M", level="R1", description="acquired resistance",
            )
        ],
    )
    out = render_oncokb_section(layer, mode="clinician")
    assert "OncoKB R1" in out
    assert "gefitinib" in out
    assert "T790M" in out
    # Block appears in the conflicts section
    assert "oncokb-conflicts-block" in out


def test_inline_track_banner_for_r1():
    conflicts = [
        ResistanceConflict(
            track_id="standard", drug="gefitinib", gene="EGFR",
            variant="T790M", level="R1", description=None,
        )
    ]
    out = render_track_resistance_banner("standard", conflicts)
    assert "OncoKB R1" in out
    assert "oncokb-inline-banner--r1" in out
    assert "gefitinib" in out


def test_inline_track_banner_for_r2_softer_styling():
    conflicts = [
        ResistanceConflict(
            track_id="standard", drug="vemurafenib", gene="BRAF",
            variant="V600E", level="R2", description=None,
        )
    ]
    out = render_track_resistance_banner("standard", conflicts)
    assert "oncokb-inline-banner--r2" in out
    assert "preclinical" in out


def test_inline_track_banner_filters_by_track_id():
    """Only conflicts for the given track surface in that track's banner."""
    conflicts = [
        ResistanceConflict(track_id="standard", drug="x", gene="G", variant="V", level="R1", description=None),
        ResistanceConflict(track_id="aggressive", drug="y", gene="G", variant="V", level="R1", description=None),
    ]
    standard_out = render_track_resistance_banner("standard", conflicts)
    assert "drug" not in standard_out  # generic
    assert "x" in standard_out
    assert "y" not in standard_out


# ── Empty layer skipped entirely ────────────────────────────────────────


def test_none_layer_returns_empty():
    assert render_oncokb_section(None, mode="clinician") == ""


def test_empty_layer_returns_empty():
    assert render_oncokb_section(OncoKBLayer(), mode="clinician") == ""


def test_layer_with_only_errors_returns_empty():
    """Errors alone don't justify a section."""
    from knowledge_base.engine.oncokb_types import OncoKBError
    q = OncoKBQuery(gene="X", variant="Y", oncotree_code=None, source_biomarker_id="BIO-x")
    layer = OncoKBLayer(errors=[OncoKBError(query=q, error_kind="timeout", detail="t")])
    assert render_oncokb_section(layer, mode="clinician") == ""
