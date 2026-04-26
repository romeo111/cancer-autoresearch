"""Tests for Phase D cron entrypoint (scripts/cron_kb_audit_runner.py).

Focus: lock acquisition + kill switch + abort logging. Pre-flight
gates and full pipelines are tested via Phase A/B/C unit tests; here
we verify the orchestration layer that ties them together.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest


def _import_runner():
    import sys
    REPO_ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(REPO_ROOT))
    import scripts.cron_kb_audit_runner as runner_mod  # noqa: E402
    return runner_mod


# ── Lock acquisition ────────────────────────────────────────────────────


def test_acquire_lock_succeeds_when_no_existing(monkeypatch, tmp_path):
    runner = _import_runner()
    monkeypatch.setattr(runner, "LOCK_FILE", tmp_path / "lock")
    ok, msg = runner.acquire_lock()
    assert ok is True
    assert (tmp_path / "lock").is_file()


def test_acquire_lock_refuses_when_recent_lock_held(monkeypatch, tmp_path):
    runner = _import_runner()
    monkeypatch.setattr(runner, "LOCK_FILE", tmp_path / "lock")
    # Drop a fresh lock
    (tmp_path / "lock").write_text(json.dumps({
        "sessionId": "other", "pid": 1, "acquiredAt": int(time.time() * 1000),
    }), encoding="utf-8")
    ok, msg = runner.acquire_lock()
    assert ok is False
    assert "lock held" in msg


def test_acquire_lock_takes_over_stale_lock(monkeypatch, tmp_path):
    runner = _import_runner()
    monkeypatch.setattr(runner, "LOCK_FILE", tmp_path / "lock")
    # Drop a >1h-old lock
    stale_ts = int((time.time() - 7200) * 1000)
    (tmp_path / "lock").write_text(json.dumps({
        "sessionId": "old", "pid": 1, "acquiredAt": stale_ts,
    }), encoding="utf-8")
    ok, _ = runner.acquire_lock()
    assert ok is True
    # New lock should have a fresh timestamp
    new = json.loads((tmp_path / "lock").read_text(encoding="utf-8"))
    assert new["acquiredAt"] > stale_ts


def test_acquire_lock_treats_corrupt_lock_as_stale(monkeypatch, tmp_path):
    runner = _import_runner()
    monkeypatch.setattr(runner, "LOCK_FILE", tmp_path / "lock")
    (tmp_path / "lock").write_text("not json {", encoding="utf-8")
    ok, _ = runner.acquire_lock()
    assert ok is True


def test_release_lock_idempotent_when_already_gone(monkeypatch, tmp_path):
    runner = _import_runner()
    monkeypatch.setattr(runner, "LOCK_FILE", tmp_path / "missing")
    runner.release_lock()  # should not raise


# ── Kill switch ─────────────────────────────────────────────────────────


def test_kill_switch_inactive_when_file_missing(monkeypatch, tmp_path):
    runner = _import_runner()
    monkeypatch.setattr(runner, "KILL_SWITCH", tmp_path / "nope")
    assert runner.kill_switch_active() is False


def test_kill_switch_active_when_file_present(monkeypatch, tmp_path):
    runner = _import_runner()
    monkeypatch.setattr(runner, "KILL_SWITCH", tmp_path / "disabled.md")
    (tmp_path / "disabled.md").write_text("disabled by maintainer", encoding="utf-8")
    assert runner.kill_switch_active() is True


# ── Top-level run() — kill switch path ──────────────────────────────────


def test_run_aborts_when_kill_switch_active(monkeypatch, tmp_path):
    runner = _import_runner()
    monkeypatch.setattr(runner, "LOCK_FILE", tmp_path / "lock")
    monkeypatch.setattr(runner, "KILL_SWITCH", tmp_path / "disabled.md")
    monkeypatch.setattr(runner, "AUDIT_LOG_DIR", tmp_path / "audit_log")
    (tmp_path / "disabled.md").write_text("disabled", encoding="utf-8")

    code = runner.run(dry_run=True)
    assert code == 2
    # Log file written even on disabled-abort (heartbeat invariant)
    log_files = list((tmp_path / "audit_log").glob("*-disabled.md"))
    assert len(log_files) == 1
    # Lock released after abort
    assert not (tmp_path / "lock").is_file()


def test_run_aborted_log_entry_named_with_suffix_on_collision(monkeypatch, tmp_path):
    runner = _import_runner()
    monkeypatch.setattr(runner, "AUDIT_LOG_DIR", tmp_path)
    runner._write_aborted_log_entry("first failure")
    runner._write_aborted_log_entry("second failure")
    files = list(tmp_path.glob("*-aborted*.md"))
    names = {f.name for f in files}
    assert len(files) == 2, f"got {names}"
    # First write uses the no-suffix form; collision write adds -2.
    assert any("-aborted.md" in n and "-aborted-" not in n for n in names)
    assert any("-aborted-2.md" in n for n in names)


# ── Lock contention ─────────────────────────────────────────────────────


def test_run_returns_2_when_lock_contention(monkeypatch, tmp_path):
    runner = _import_runner()
    monkeypatch.setattr(runner, "LOCK_FILE", tmp_path / "lock")
    monkeypatch.setattr(runner, "KILL_SWITCH", tmp_path / "no_kill")
    monkeypatch.setattr(runner, "AUDIT_LOG_DIR", tmp_path / "audit_log")
    # Drop a fresh competitor lock
    (tmp_path / "lock").write_text(json.dumps({
        "sessionId": "other", "pid": 999, "acquiredAt": int(time.time() * 1000),
    }), encoding="utf-8")

    code = runner.run(dry_run=True)
    assert code == 2


# ── State patching after executor returns issue numbers ────────────────


def test_patch_state_file_updates_issue_numbers(monkeypatch, tmp_path):
    runner = _import_runner()
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({
        "open_issues": {
            "kb-audit-key-v1:foo:bar": None,
            "kb-audit-key-v1:other:keep": 42,
        },
    }), encoding="utf-8")
    monkeypatch.setattr(runner, "STATE_FILE", state_path)

    runner._patch_state_file_issue_numbers({
        "kb-audit-key-v1:foo:bar": 77,
    })

    updated = json.loads(state_path.read_text(encoding="utf-8"))
    assert updated["open_issues"]["kb-audit-key-v1:foo:bar"] == 77
    assert updated["open_issues"]["kb-audit-key-v1:other:keep"] == 42


def test_patch_state_file_skips_when_state_missing(monkeypatch, tmp_path):
    runner = _import_runner()
    monkeypatch.setattr(runner, "STATE_FILE", tmp_path / "no-state.json")
    # Should not raise
    runner._patch_state_file_issue_numbers({"k": 1})


# ── Dry-run path: full integration without git/gh side effects ─────────


def test_dry_run_completes_without_writing_state(monkeypatch, tmp_path):
    """In --dry-run we build the plan but do NOT write state file or
    audit log markdown. (Tests the full cron pipeline gracefully
    short-circuits when dry-run is requested.)"""
    runner = _import_runner()
    monkeypatch.setattr(runner, "LOCK_FILE", tmp_path / "lock")
    monkeypatch.setattr(runner, "KILL_SWITCH", tmp_path / "no_kill")
    monkeypatch.setattr(runner, "AUDIT_LOG_DIR", tmp_path / "audit_log")
    monkeypatch.setattr(runner, "STATE_FILE", tmp_path / "state.json")

    code = runner.run(dry_run=True)
    # Returns 0 (success); state file NOT written
    assert code == 0
    assert not (tmp_path / "state.json").is_file()
    # Lock released even in dry-run
    assert not (tmp_path / "lock").is_file()
