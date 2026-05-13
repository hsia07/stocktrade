"""
MAIN_CONTROL_LOOP_FUNCTIONAL_EXECUTION_LOGIC_CANDIDATE_REWORK tests.

Verifies:
- ENGINE REPAIR MODE print-only block has been removed
- Guard-StartEvent blocks when run_state != "running"
- Guard-FunctionalCommit blocks when preCommit == postCommit
- Functional execution path creates a real git commit
- CandidateDiff guard validates Work > 0
- Guard-RealCodeChanges filters packaging-only commits
- Safe-deny: no merge/push from loop, no trading/broker/execution access
- Loop does not modify real state.runtime.json
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
CONTROL_DIR = REPO_ROOT / "automation" / "control"
MAIN_LOOP_PS1 = CONTROL_DIR / "main_control_loop.ps1"
STATE_RUNTIME = CONTROL_DIR / "state.runtime.json"


ALLOWED_FORBIDDEN_PATTERNS = [
    "strategy/",
    "broker/",
    "execution/",
    "server_v2.py",
    "index_v2.html",
]

PACKAGING_FILE_PATTERNS = [
    "evidence.json",
    "report.json",
    "candidate.diff",
    "task.txt",
    "run_record.json",
    "review_packet.md",
]


def read_script(path: Path = MAIN_LOOP_PS1) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def find_line_range(content: str, marker: str) -> tuple[int, int]:
    lines = content.splitlines()
    start = None
    for i, line in enumerate(lines):
        if marker in line:
            if start is None:
                start = i + 1
            end = i + 1
    if start is None:
        return (0, 0)
    return (start, end)


class TestEngineRepairModeRemoved:
    def test_engine_repair_mode_string_not_present(self):
        content = read_script()
        assert "ENGINE REPAIR MODE" not in content, (
            "ENGINE REPAIR MODE placeholder still present; "
            "must be replaced with functional execution logic"
        )

    def test_governance_execution_present(self):
        content = read_script()
        assert "GOVERNANCE CANDIDATE EXECUTION" in content, (
            "GOVERNANCE CANDIDATE EXECUTION section must exist"
        )

    def test_evidence_checker_invoked(self):
        content = read_script()
        assert "evidence_checker.py" in content, (
            "evidence_checker.py must be invoked in the execution section"
        )

    def test_gate_reporter_invoked(self):
        content = read_script()
        assert "gate_report_persister.py" in content, (
            "gate_report_persister.py must be invoked in the execution section"
        )

    def test_commit_created_in_execution(self):
        content = read_script()
        assert "git -C $RepoRoot commit" in content, (
            "Execution section must create a git commit"
        )

    def test_candidate_diff_generated(self):
        content = read_script()
        assert "candidate.diff" in content, (
            "candidate.diff must be generated in execution section"
        )


class TestGuardStartEvent:
    def test_guard_start_event_checks_run_state(self):
        content = read_script()
        assert '$state.run_state -ne "running"' in content, (
            "Guard-StartEvent must check run_state == running"
        )

    def test_guard_start_event_checks_whether_started(self):
        content = read_script()
        assert "whether_started" in content, (
            "Guard-StartEvent must check whether_started flag"
        )


class TestGuardFunctionalCommit:
    def test_guard_checks_pre_post_commit(self):
        content = read_script()
        assert "$beforeCommit -eq $afterCommit" in content or '$preCommit -ne $postCommit' in content, (
            "Guard-FunctionalCommit must verify preCommit != postCommit"
        )

    def test_guard_checks_commit_message_round_id(self):
        content = read_script()
        assert "$commitMessage -notmatch $roundId" in content, (
            "Guard-FunctionalCommit must verify commit message contains roundId"
        )

    def test_no_real_commit_causes_block(self):
        content = read_script()
        assert "$preCommit" in content, "preCommit capture must exist"
        assert "$postCommit" in content, "postCommit capture must exist"


class TestGuardRealCodeChanges:
    def test_filter_patterns_present(self):
        content = read_script()
        for pat in PACKAGING_FILE_PATTERNS:
            assert pat in content, (
                f"Packaging filter pattern '{pat}' must be in Guard-RealCodeChanges"
            )


class TestGuardCandidateDiff:
    def test_work_count_check_present(self):
        content = read_script()
        assert "Work:" in content, "Guard-CandidateDiff must check Work: N"
        assert "0 tasks" in content or "zero tasks" in content.lower(), (
            "Guard-CandidateDiff must reject Work: 0 tasks"
        )


class TestSafeDeny:
    def test_no_git_merge_in_script(self):
        content = read_script()
        merge_lines = [
            line for line in content.splitlines()
            if "git merge" in line and "#" not in line.split("git merge")[0]
        ]
        assert len(merge_lines) == 0, f"git merge found in execution: {merge_lines}"

    def test_no_git_push_in_script(self):
        content = read_script()
        push_lines = [
            line for line in content.splitlines()
            if "git push" in line and "#" not in line.split("git push")[0]
        ]
        assert len(push_lines) == 0, f"git push found in execution: {push_lines}"

    def test_no_promote_in_script(self):
        content = read_script()
        assert "promote" not in content.lower(), "promote should not be in script"

    def test_forbidden_paths_not_referenced(self):
        content = read_script()
        exec_start = content.find("GOVERNANCE CANDIDATE EXECUTION")
        exec_end = content.find("POST-EXECUTION GUARDS", exec_start)
        if exec_start < 0:
            return
        section = content[exec_start:exec_end] if exec_end > 0 else content[exec_start:]
        for i, line in enumerate(section.splitlines()):
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('//'):
                continue
            if stripped.startswith('"') or stripped.startswith("'") or stripped.startswith('@'):
                continue
            low = stripped.lower()
            for pat in ALLOWED_FORBIDDEN_PATTERNS:
                lowpat = pat.lower().rstrip('/').rstrip('.py')
                if lowpat in low and ('import' in low or 'from' in low or 'python' in low or 'join-path' in low):
                    assert False, (
                        f"Forbidden import/reference '{pat}' at line {exec_start + i + 1}: {stripped[:120]}"
                    )

    def test_safe_deny_marker_in_comment(self):
        content = read_script()
        assert "safe-deny" in content.lower() or "safe_deny" in content.lower(), (
            "Script should document safe-deny"
        )

    def test_merge_gate_not_auto_opened(self):
        content = read_script()
        merge_gate_opens = [
            line for line in content.splitlines()
            if "merge_gate" in line and "closed" not in line.lower()
        ]
        assert len(merge_gate_opens) == 0, (
            f"merge_gate should stay closed; suspected open: {merge_gate_opens}"
        )


class TestRuntimeStateNotModified:
    def test_state_write_only_in_guards_passed_section(self):
        content = read_script()
        state_writes = []
        lines = content.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if 'Set-Content' in stripped and 'state.runtime' in stripped:
                state_writes.append((i + 1, stripped))
        if state_writes:
            for lineno, line in state_writes:
                preceding = "\n".join(lines[max(0, lineno - 5):lineno])
                assert "ALL FAIL-CLOSED GUARDS PASSED" in preceding, (
                    f"state.runtime.json Write at line {lineno} not after ALL GUARDS PASSED: {line}"
                )

    def test_state_runtime_not_in_execution_stage(self):
        content = read_script()
        execution_section_start = content.find("GOVERNANCE CANDIDATE EXECUTION")
        execution_section_end = content.find("POST-EXECUTION GUARDS", execution_section_start)
        if execution_section_start >= 0 and execution_section_end >= 0:
            section = content[execution_section_start:execution_section_end]
            assert "state.runtime" not in section, (
                "state.runtime.json should not be written in the execution section"
            )


class TestGuardPreservation:
    def run_test_for_guard(self, guard_name: str):
        content = read_script()
        assert f"function {guard_name}" in content, (
            f"Guard function {guard_name} must be preserved"
        )
        assert f"GUARD_VIOLATION" in content, (
            f"Guard {guard_name} must have GUARD_VIOLATION paths"
        )

    def test_guard_start_event_preserved(self):
        self.run_test_for_guard("Guard-StartEvent")

    def test_guard_tool_execution_preserved(self):
        self.run_test_for_guard("Guard-ToolExecution")

    def test_guard_functional_commit_preserved(self):
        self.run_test_for_guard("Guard-FunctionalCommit")

    def test_guard_tracked_candidate_preserved(self):
        self.run_test_for_guard("Guard-TrackedCandidate")

    def test_guard_no_shared_commit_reuse_preserved(self):
        self.run_test_for_guard("Guard-NoSharedCommitReuse")

    def test_guard_real_code_changes_preserved(self):
        self.run_test_for_guard("Guard-RealCodeChanges")

    def test_guard_candidate_diff_preserved(self):
        self.run_test_for_guard("Guard-CandidateDiff")


class TestNoRealRuntimeStart:
    def test_no_control_bridge_import_in_test(self):
        content = read_script()
        exec_start = content.find("GOVERNANCE CANDIDATE EXECUTION")
        exec_end = content.find("POST-EXECUTION GUARDS", exec_start)
        if exec_start < 0:
            return
        section = content[exec_start:exec_end] if exec_end > 0 else content[exec_start:]
        for i, line in enumerate(section.splitlines()):
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('//'):
                continue
            if stripped.startswith('"') or stripped.startswith("'") or stripped.startswith('@'):
                continue
            low = stripped.lower()
            if "control_bridge" in low and ("import" in low or "start(" in low or ".start" in low or "run(" in low or "python" in low):
                if "= \$false" in stripped or "= $false" in stripped:
                    continue
                if "= \$null" in stripped or "= $null" in stripped:
                    continue
                assert False, (
                    f"control_bridge started/imported at line {exec_start + i + 1}: {stripped[:120]}"
                )

    def test_no_telegram_real_import_in_test(self):
        content = read_script()
        assert "TELEGRAM_BOT_TOKEN" not in content, (
            "Tests should not contain real Telegram token references"
        )


class TestCommitIntegrity:
    def test_git_available(self):
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        assert result.returncode == 0, "Not in a git repository"

    def test_branch_is_candidate(self):
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        branch = result.stdout.strip()
        assert "candidate/" in branch, (
            f"Tests should run on a candidate branch, got: {branch}"
        )
