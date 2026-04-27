"""Actionability render tests — phase-4 redefined.

Renamed from test_oncokb_render.py during the CIViC pivot. The previous
implementation tested `engine.render_oncokb.render_oncokb_section`,
which was removed in Phase 1 — the OncoKB-shaped layer / banner output
is gone. Phase 4 will rebuild a CIViC-shaped section renderer
(`engine.render_actionability.render_actionability_section`) and these
tests will be reinstated in source-agnostic form.

The contract every test below pins (defense-in-depth for AC-3) is still
enforced elsewhere:
  - patient-mode never emits actionability content → AC-3 covered by
    `tests/test_patient_render.py`
  - resistance-conflict detector → covered (skipped until matchers
    populate RESISTANCE_LEVELS) by `test_actionability_invariants.py`
"""

from __future__ import annotations

import pytest

# Phase 1 removed the section renderer — every test in this module was
# coupled to it. Skip the whole module until Phase 4 lands the CIViC
# section renderer; deleting the file would lose the contract
# documentation, which is the load-bearing artifact here.
pytest.skip(
    "phase-2/4: render_actionability_section pending CIViC reader — "
    "see docs/reviews/oncokb-public-civic-coverage-2026-04-27.md",
    allow_module_level=True,
)
