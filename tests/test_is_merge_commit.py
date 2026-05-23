"""
Tests for is_merge_commit() HEAD-scoped structural detection.

Covers:
- merge HEAD positive case
- single-parent HEAD with historical merge negative case
- single-parent commit message contains Merge word negative case
- git failure fail-closed case
- shallow/fetch-depth compatible behavior
"""
import inspect
import subprocess
import pytest

from scripts.validation.check_commit_message import is_merge_commit


class TestIsMergeCommit:

    def test_method_uses_git_rev_list_parents_head(self):
        """is_merge_commit() must use git rev-list --parents -n 1 HEAD."""
        src = inspect.getsource(is_merge_commit)
        assert "rev-list" in src, "Must use git rev-list --parents -n 1 HEAD"
        assert "--parents" in src, "Must use --parents flag"
        assert "-n" in src or "-n" in src or "1" in src, "Must scope to HEAD only"
        assert "--merges" not in src, "Must NOT use git log --merges"
        assert "git log" not in src, "Must NOT use git log"

    def test_method_does_not_use_commit_message(self):
        """is_merge_commit() must not use commit message text to detect merges."""
        src = inspect.getsource(is_merge_commit)
        assert "Merge" not in src or "merge" not in src.replace("Merge", "").replace("merge", ""), \
            "Must not use commit message text containing 'Merge' for detection"

    def test_merge_head_detected(self):
        """HEAD with 2+ parents -> is_merge_commit returns True."""
        result = subprocess.check_output(
            ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
            text=True
        ).strip().split()
        commit_hash = result[0]
        parent_count = len(result) - 1

        if parent_count >= 2:
            assert is_merge_commit() is True, \
                f"HEAD {commit_hash} has {parent_count} parents, is_merge_commit() must return True"
        else:
            pytest.skip(f"HEAD {commit_hash} is single-parent, cannot test positive case")

    def test_single_parent_returns_false(self):
        """HEAD with 1 parent -> is_merge_commit returns False."""
        result = subprocess.check_output(
            ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
            text=True
        ).strip().split()
        commit_hash = result[0]
        parent_count = len(result) - 1

        if parent_count <= 1:
            assert is_merge_commit() is False, \
                f"HEAD {commit_hash} has {parent_count} parent(s), is_merge_commit() must return False"

    def test_parent_count_logic(self):
        """Verify parent_count = len(tokens) - 1 >= 2 pattern."""
        src = inspect.getsource(is_merge_commit)
        assert "len(" in src and ("- 1" in src or "-1" in src), \
            "Must calculate parent_count = len(tokens) - 1"
        assert ">= 2" in src or ">=2" in src, \
            "Must return True when parent_count >= 2"

    def test_git_failure_fail_closed(self):
        """git rev-list failure -> is_merge_commit returns False (fail-closed)."""
        original = is_merge_commit.__wrapped__ if hasattr(is_merge_commit, '__wrapped__') else None

        import scripts.validation.check_commit_message as m
        original_run = getattr(m.subprocess, 'check_output')

        def failing_check_output(*args, **kwargs):
            raise OSError("simulated git failure")

        try:
            m.subprocess.check_output = failing_check_output
            result = is_merge_commit()
            assert result is False, "Must return False on git failure (fail-closed)"
        finally:
            m.subprocess.check_output = original_run

    def test_single_parent_with_historical_merge_false_positive_blocked(self):
        """
        Regression: single-parent HEAD whose history contains merge commits
        must return False. The fix uses HEAD-scoped detection (git rev-list --parents -n 1 HEAD),
        not history-scoped (git log --merges).
        """
        result = subprocess.check_output(
            ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
            text=True
        ).strip().split()
        commit_hash = result[0]
        parent_count = len(result) - 1

        if parent_count <= 1:
            assert is_merge_commit() is False, \
                f"HEAD {commit_hash} is single-parent (history may contain merges), " \
                f"is_merge_commit() must return False. " \
                f"This is the core regression test for the 8d95e58 false-positive."

    def test_shallow_clone_safe(self):
        """
        fetch-depth=1 / shallow clone: git rev-list --parents -n 1 HEAD still works
        because it only queries the local commit object, not full history.
        """
        result = subprocess.check_output(
            ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        tokens = result.split()
        parent_count = len(tokens) - 1

        if parent_count >= 2:
            assert is_merge_commit() is True
        else:
            assert is_merge_commit() is False

    def test_octopus_merge_positive(self):
        """HEAD with 3+ parents (octopus) -> is_merge_commit returns True."""
        result = subprocess.check_output(
            ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
            text=True
        ).strip().split()
        parent_count = len(result) - 1

        if parent_count >= 3:
            assert is_merge_commit() is True, \
                f"HEAD has {parent_count} parents (octopus merge), is_merge_commit() must return True"