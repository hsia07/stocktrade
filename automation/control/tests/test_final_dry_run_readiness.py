import pytest
import json
import os
import subprocess
import tempfile
from pathlib import Path

from automation.control.dry_run_readiness import DryRunReadinessChecker


@pytest.fixture
def checker():
    repo_root = Path(__file__).parent.parent.parent.parent.resolve()
    return DryRunReadinessChecker(
        repo_root=repo_root,
        expected_canonical_head="",
        expected_branch="work/canonical-mainline-repair-001",
        mock_mode=True,
    )


def _run_git(repo_root, *args):
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, timeout=30,
        cwd=str(repo_root),
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def test_dry_run_returns_not_ready_when_untracked_paths_exist(checker):
    report = checker.check_all()
    if checker.untracked_paths_count > 0:
        assert report["ready"] is False
        assert "untracked_paths" in str(checker.blockers) or any("untracked" in b for b in checker.blockers)
    else:
        assert report["untracked_paths_count"] == 0


def test_dry_run_checks_local_remote_head(checker):
    report = checker.check_all()
    git_state = report["results"]["git_state"]
    assert "canonical_local_head" in git_state
    assert "canonical_remote_head" in git_state
    assert "local_remote_heads_match" in git_state


def test_dry_run_detects_head_mismatch(checker):
    checker.expected_canonical_head = "NONEXISTENT_HASH_12345"
    report = checker.check_all()
    git_state = report["results"]["git_state"]
    if git_state.get("canonical_local_head"):
        assert git_state["canonical_head_matches_expected"] is False


def test_dry_run_checks_tracked_clean(checker):
    report = checker.check_all()
    git_state = report["results"]["git_state"]
    assert "tracked_files_clean" in git_state
    assert isinstance(git_state["tracked_files_clean"], bool)


def test_dry_run_verifies_telegram_inbound_readiness(checker):
    report = checker.check_all()
    inbound = report["results"]["telegram_inbound_readiness"]
    assert "passed" in inbound
    assert "failures" in inbound


def test_dry_run_verifies_undefined_round_gate(checker):
    report = checker.check_all()
    gate = report["results"]["undefined_round_gate"]
    assert "passed" in gate


def test_dry_run_verifies_usage_exhaustion_notify(checker):
    report = checker.check_all()
    usage = report["results"]["usage_exhaustion_notify"]
    assert "passed" in usage


def test_dry_run_verifies_all_6_notification_types(checker):
    report = checker.check_all()
    notif = report["results"]["notification_coverage"]
    assert "method_count" in notif
    assert notif["method_count"] >= 6
    assert "send_pause_notification" in str(notif["notification_methods"])
    assert "send_usage_exhausted_notification" in str(notif["notification_methods"])
    assert "send_blocked_notification" in str(notif["notification_methods"])
    assert "send_awaiting_instruction_notification" in str(notif["notification_methods"])
    assert "send_undefined_round_blocked_notification" in str(notif["notification_methods"])


def test_dry_run_verifies_kill_switch(checker):
    report = checker.check_all()
    kill = report["results"]["kill_switch"]
    assert "passed" in kill
    assert "commands_available" in kill
    assert "/pause" in kill["commands_available"]
    assert "/start" in kill["commands_available"]
    assert "/status" in kill["commands_available"]


def test_dry_run_does_not_dispatch_construction(checker):
    report = checker.check_all()
    inv = report["results"]["dry_run_invariants"]
    assert inv["construction_not_triggered"] is True
    assert inv["next_round_not_dispatched"] is True
    assert inv["candidate_not_created"] is True


def test_dry_run_does_not_create_candidate(checker):
    report = checker.check_all()
    inv = report["results"]["dry_run_invariants"]
    assert inv["candidate_not_created"] is True


def test_dry_run_does_not_commit_merge_push(checker):
    report = checker.check_all()
    inv = report["results"]["dry_run_invariants"]
    assert inv["no_commit"] is True
    assert inv["no_merge"] is True
    assert inv["no_push"] is True
    assert inv["no_promote"] is True
    assert inv["no_pr"] is True


def test_dry_run_does_not_send_real_telegram_http(checker):
    report = checker.check_all()
    inv = report["results"]["dry_run_invariants"]
    assert inv["no_real_telegram_http"] is True


def test_dry_run_emits_machine_readable_json_report(checker):
    report = checker.check_all()
    json_str = checker.report_json()
    parsed = json.loads(json_str)
    assert "ready" in parsed
    assert "all_passed" in parsed
    assert "blockers" in parsed
    assert "results" in parsed
    assert "git_state" in parsed["results"]
    assert "prior_batches" in parsed["results"]
    assert "telegram_inbound_readiness" in parsed["results"]
    assert "undefined_round_gate" in parsed["results"]
    assert "usage_exhaustion_notify" in parsed["results"]
    assert "notification_coverage" in parsed["results"]
    assert "kill_switch" in parsed["results"]
    assert "mock_mode_safety" in parsed["results"]
    assert "dry_run_invariants" in parsed["results"]


def test_dry_run_emits_chatgpt_readable_summary(checker):
    checker.check_all()
    summary = checker.summary_chatgpt()
    assert "=== Dry-Run Readiness Summary ===" in summary
    assert "Status:" in summary
    assert "Canonical HEAD:" in summary
    assert "Blockers:" in summary or "All Checks Passed:" in summary


def test_dry_run_report_contains_all_required_fields(checker):
    report = checker.check_all()
    assert "canonical_local_head" in report
    assert "canonical_remote_head" in report
    assert "expected_canonical_head" in report
    assert "local_remote_heads_match" in report
    assert "canonical_head_matches_expected" in report
    assert "tracked_files_clean" in report
    assert "untracked_paths_count" in report
    assert isinstance(report["untracked_paths_count"], int)


def test_dry_run_checks_prior_batches(checker):
    report = checker.check_all()
    batches = report["results"]["prior_batches"]
    assert "batches" in batches
    batch_names = [b["batch_name"] for b in batches["batches"]]
    assert "TELEGRAM_INBOUND_HARDENING" in batch_names
    assert "UNDEFINED_ROUND_HARD_GATE_BATCH" in batch_names
    assert "USAGE_EXHAUSTION_PAUSE_NOTIFY_BATCH" in batch_names


def test_dry_run_secrets_not_exposed(checker):
    report = checker.check_all()
    json_str = json.dumps(report)
    sensitive_patterns = [
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        "bot_token", "api_key", "apikey",
    ]
    for pattern in sensitive_patterns:
        assert pattern not in json_str


def test_dry_run_returns_not_ready_when_blockers(checker):
    checker.expected_canonical_head = "INVALID_HASH_FOR_TESTING"
    report = checker.check_all()
    git_state = report["results"]["git_state"]
    if git_state.get("canonical_local_head"):
        assert report["all_passed"] is False


def test_mock_mode_no_real_api_calls():
    checker = DryRunReadinessChecker(mock_mode=True)
    assert checker.mock_mode is True
    report = checker.check_all()
    inv = report["results"]["dry_run_invariants"]
    assert inv["no_real_telegram_http"] is True


def test_dry_run_does_not_touch_forbidden_paths(checker):
    report = checker.check_all()
    inv = report["results"]["dry_run_invariants"]
    assert inv["secrets_not_touched"] is True
    assert inv["runtime_not_touched"] is True
    assert inv["retained_untracked_not_touched"] is True


def test_dry_run_round_trip_json(checker):
    checker.check_all()
    json_str = checker.report_json()
    parsed = json.loads(json_str)
    assert parsed["ready"] == checker.all_passed
    assert parsed["all_passed"] == checker.all_passed
    assert len(parsed["blockers"]) == len(checker.blockers)
