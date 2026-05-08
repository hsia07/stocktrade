"""
BLOCKER_D runtime tests: pre-push hook PowerShell rewrite.

Verifies:
- .githooks/pre-push.ps1 contains all governance checks
- PowerShell syntax is valid
- Non-canonical branch pushes pass
- Single-parent canonical pushes blocked
- Merge commit canonical pushes (with Law 04) pass
- Force push detection works
- .bat entry point exists and references .ps1
- Bash hook preserved (not deleted)
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
HOOKS_DIR = REPO_ROOT / ".githooks"
CANONICAL_MERGE_COMMIT = "72bbfb1f94f0ee2fe6fe9e2f82fc2d933ba47765"
CANONICAL_PARENT = "46dea3bf6fff09b7b1e04fda2b48403345f9bcfc"
SINGLE_PARENT_COMMIT = "6408859efa3a9af0156a6caaf98ff6e97fde95f5"
ZERO_SHA = "0000000000000000000000000000000000000"


def run_ps1(stdin_text: str) -> subprocess.CompletedProcess:
    """Run pre-push.ps1 with given stdin, return result."""
    ps1_path = HOOKS_DIR / "pre-push.ps1"
    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(ps1_path),
    ]
    return subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO_ROOT),
    )


class TestPowerShellHookExists:
    """Hook file existence and basic integrity."""

    def test_ps1_hook_exists(self) -> None:
        assert HOOKS_DIR.exists()
        assert (HOOKS_DIR / "pre-push.ps1").exists()

    def test_ps1_hook_not_empty(self) -> None:
        content = (HOOKS_DIR / "pre-push.ps1").read_text(encoding="utf-8")
        assert len(content) > 100

    def test_bat_entry_point_exists(self) -> None:
        """The .bat entry point must exist and reference the .ps1."""
        bat_path = HOOKS_DIR / "pre-push.bat"
        assert bat_path.exists()
        content = bat_path.read_text(encoding="utf-8")
        assert "pre-push.ps1" in content

    def test_bash_hook_preserved(self) -> None:
        """Bash hook must NOT be deleted."""
        bash_path = HOOKS_DIR / "pre-push"
        assert bash_path.exists()
        content = bash_path.read_text(encoding="utf-8")
        assert "#!/bin/bash" in content


class TestPowerShellHookContent:
    """Content-based verification of governance checks."""

    def test_contains_canonical_branch_detection(self) -> None:
        content = (HOOKS_DIR / "pre-push.ps1").read_text(encoding="utf-8")
        assert "canonical" in content.lower()
        assert "main|work/canonical" in content

    def test_contains_merge_commit_detection(self) -> None:
        content = (HOOKS_DIR / "pre-push.ps1").read_text(encoding="utf-8")
        assert "Get-ParentCount" in content or "cat-file -p" in content
        assert "parent" in content.lower()
        assert "2" in content or "parentCount" in content

    def test_contains_law04_compliance(self) -> None:
        content = (HOOKS_DIR / "pre-push.ps1").read_text(encoding="utf-8")
        assert "law_compliance" in content
        assert "04" in content

    def test_contains_single_parent_block(self) -> None:
        content = (HOOKS_DIR / "pre-push.ps1").read_text(encoding="utf-8")
        assert "UNAUTHORIZED PUSH BLOCKED" in content
        assert "Single-parent" in content

    def test_contains_force_push_block(self) -> None:
        content = (HOOKS_DIR / "pre-push.ps1").read_text(encoding="utf-8")
        assert "Force push" in content
        assert "force-with-lease" in content.lower()

    def test_contains_evidence_json_scan(self) -> None:
        content = (HOOKS_DIR / "pre-push.ps1").read_text(encoding="utf-8")
        assert "evidence.json" in content
        assert "diff-tree" in content
        assert "diff-filter=AM" in content


class TestPowerShellHookExecution:
    """Runtime execution tests (requires Windows + PowerShell)."""

    def test_non_canonical_branch_passes(self) -> None:
        stdin = (
            f"refs/heads/feature/test {ZERO_SHA} "
            f"refs/heads/feature/other {ZERO_SHA}\n"
        )
        result = run_ps1(stdin)
        assert result.returncode == 0, (
            f"Non-canonical push should pass, got rc={result.returncode}, "
            f"stderr={result.stderr}, stdout={result.stdout}"
        )

    def test_single_parent_canonical_blocked(self) -> None:
        stdin = (
            f"refs/heads/work/canonical-test {ZERO_SHA} "
            f"refs/heads/work/canonical-test {ZERO_SHA}\n"
        )
        result = run_ps1(stdin)
        assert result.returncode == 1, (
            f"Single-parent canonical push should block, got rc={result.returncode}"
        )
        assert "UNAUTHORIZED PUSH BLOCKED" in result.stdout

    def test_merge_commit_canonical_passes(self) -> None:
        """Merge commit with Law 04 evidence should pass."""
        stdin = (
            f"refs/heads/work/canonical-mainline-repair-001 {CANONICAL_MERGE_COMMIT} "
            f"refs/heads/work/canonical-mainline-repair-001 {CANONICAL_PARENT}\n"
        )
        result = run_ps1(stdin)
        assert result.returncode == 0, (
            f"Merge commit should pass, got rc={result.returncode}, "
            f"stdout={result.stdout}, stderr={result.stderr}"
        )
        assert "PASS: Law 04 compliance verified" in result.stdout

    def test_no_stdin_exits_ok(self) -> None:
        """No stdin should just exit 0 (no push data to check)."""
        result = run_ps1("")
        assert result.returncode == 0
        assert "[pre-push] ok" in result.stdout

    def test_force_push_detected_blocked(self) -> None:
        """Force push: remote_sha not ancestor of local_sha (single-parent commit)."""
        stdin = (
            f"refs/heads/work/canonical-mainline-repair-001 {SINGLE_PARENT_COMMIT} "
            f"refs/heads/work/canonical-mainline-repair-001 {CANONICAL_MERGE_COMMIT}\n"
        )
        result = run_ps1(stdin)
        assert result.returncode == 1, (
            f"Force push should block, got rc={result.returncode}"
        )
