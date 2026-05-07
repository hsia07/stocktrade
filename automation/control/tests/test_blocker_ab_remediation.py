"""
Tests for BLOCKER_A (GitHashVerifier) and BLOCKER_B (WorktreeManager) remediation.
Verifies hash auto-extraction, hash verification, and worktree manager operations.
"""

import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from automation.control.git_hash_verifier import GitHashVerifier
from automation.control.worktree_manager import WorktreeManager, WORKTREE_REGISTRY, VALID_PURPOSES, WORKTREE_BASE


def test_git_hash_verifier_imports():
    """Test that GitHashVerifier can be imported and instantiated."""
    verifier = GitHashVerifier(REPO_ROOT)
    assert verifier is not None
    print("PASS: test_git_hash_verifier_imports")


def test_get_head_hash_is_40hex():
    """Test that get_head_hash() returns a valid 40-hex string."""
    verifier = GitHashVerifier(REPO_ROOT)
    head = verifier.get_head_hash()
    assert len(head) == 40, f"Expected 40 chars, got {len(head)}: {head}"
    assert all(c in "0123456789abcdef" for c in head), f"Non-hex chars: {head}"
    print(f"PASS: test_get_head_hash_is_40hex ({head})")


def test_get_head_hash_matches_git():
    """Test that get_head_hash() matches direct git rev-parse HEAD."""
    import subprocess
    verifier = GitHashVerifier(REPO_ROOT)
    head = verifier.get_head_hash()
    git_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
        cwd=str(REPO_ROOT),
    )
    git_head = git_result.stdout.strip()
    assert head == git_head, f"Mismatch: {head} vs {git_head}"
    print(f"PASS: test_get_head_hash_matches_git")


def test_verify_hash_correct():
    """Test that verify_hash() returns True for the correct hash."""
    verifier = GitHashVerifier(REPO_ROOT)
    head = verifier.get_head_hash()
    assert verifier.verify_hash(head) is True
    print("PASS: test_verify_hash_correct")


def test_verify_hash_wrong():
    """Test that verify_hash() returns False for a wrong hash."""
    verifier = GitHashVerifier(REPO_ROOT)
    wrong = "0000000000000000000000000000000000000000"
    assert verifier.verify_hash(wrong) is False
    print("PASS: test_verify_hash_wrong")


def test_assert_hash_matches_correct():
    """Test that assert_hash_matches() does NOT raise for correct hash."""
    verifier = GitHashVerifier(REPO_ROOT)
    head = verifier.get_head_hash()
    try:
        verifier.assert_hash_matches(head)
        print("PASS: test_assert_hash_matches_correct")
    except ValueError as e:
        print(f"FAIL: test_assert_hash_matches_correct raised: {e}")
        raise


def test_assert_hash_matches_wrong():
    """Test that assert_hash_matches() DOES raise for wrong hash."""
    verifier = GitHashVerifier(REPO_ROOT)
    wrong = "0000000000000000000000000000000000000000"
    try:
        verifier.assert_hash_matches(wrong)
        print("FAIL: test_assert_hash_matches_wrong did not raise")
        raise AssertionError("Expected ValueError")
    except ValueError:
        print("PASS: test_assert_hash_matches_wrong (ValueError raised)")


def test_is_valid_40hex():
    """Test is_valid_40hex() with valid and invalid inputs."""
    verifier = GitHashVerifier(REPO_ROOT)
    assert verifier.is_valid_40hex("abcd" * 10) is True
    assert verifier.is_valid_40hex("") is False
    assert verifier.is_valid_40hex("short") is False
    assert verifier.is_valid_40hex("x" * 40) is False  # not hex
    assert verifier.is_valid_40hex(None) is False
    print("PASS: test_is_valid_40hex")


def test_get_report_data():
    """Test get_report_data() returns correct structure."""
    verifier = GitHashVerifier(REPO_ROOT)
    data = verifier.get_report_data()
    assert "commit_hash" in data
    assert "commit_hash_valid_40hex" in data
    assert data["commit_hash_source"] == "auto_extracted_from_git_rev_parse_HEAD"
    assert data["commit_hash_manual_transcription"] is False
    assert data["commit_hash_valid_40hex"] is True
    print("PASS: test_get_report_data")


def test_worktree_manager_imports():
    """Test that WorktreeManager can be imported and instantiated."""
    mgr = WorktreeManager(REPO_ROOT)
    assert mgr is not None
    print("PASS: test_worktree_manager_imports")


def test_worktree_naming_convention():
    """Test get_worktree_path() naming convention."""
    mgr = WorktreeManager(REPO_ROOT)
    path = mgr.get_worktree_path("R030", "candidate")
    assert "stocktrade-R030-candidate" in str(path)
    assert path.parent == WORKTREE_BASE
    print(f"PASS: test_worktree_naming_convention ({path})")


def test_worktree_purpose_validation():
    """Test purpose validation accepts valid and rejects invalid."""
    mgr = WorktreeManager(REPO_ROOT)
    for purpose in VALID_PURPOSES:
        mgr._validate_purpose(purpose)  # should not raise
    try:
        mgr._validate_purpose("invalid")
        print("FAIL: test_worktree_purpose_validation (invalid passed)")
    except ValueError:
        print("PASS: test_worktree_purpose_validation")


def test_worktree_round_id_validation():
    """Test round_id validation rejects non-R format."""
    mgr = WorktreeManager(REPO_ROOT)
    try:
        mgr._validate_round_id("invalid")
        print("FAIL: test_worktree_round_id_validation (invalid passed)")
    except ValueError:
        print("PASS: test_worktree_round_id_validation")


def test_list_active_worktrees():
    """Test list_active_worktrees() returns a list."""
    mgr = WorktreeManager(REPO_ROOT)
    worktrees = mgr.list_active_worktrees()
    assert isinstance(worktrees, list)
    print(f"PASS: test_list_active_worktrees ({len(worktrees)} worktrees)")


def test_verify_baseline_no_registry():
    """Test verify_baseline() returns False when no registry entry exists."""
    mgr = WorktreeManager(REPO_ROOT)
    result = mgr.verify_baseline("R999", "candidate")
    assert result is False
    print("PASS: test_verify_baseline_no_registry")


if __name__ == "__main__":
    tests = [
        test_git_hash_verifier_imports,
        test_get_head_hash_is_40hex,
        test_get_head_hash_matches_git,
        test_verify_hash_correct,
        test_verify_hash_wrong,
        test_assert_hash_matches_correct,
        test_assert_hash_matches_wrong,
        test_is_valid_40hex,
        test_get_report_data,
        test_worktree_manager_imports,
        test_worktree_naming_convention,
        test_worktree_purpose_validation,
        test_worktree_round_id_validation,
        test_list_active_worktrees,
        test_verify_baseline_no_registry,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
