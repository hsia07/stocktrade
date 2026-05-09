import subprocess
from pathlib import Path

HOOK = Path(__file__).parent.parent.parent.parent / ".githooks" / "pre-push.ps1"


def test_hook_exists():
    assert HOOK.exists(), f"pre-push.ps1 not found at {HOOK}"
    print("PASS: test_hook_exists")


def test_hook_contains_naming_function():
    content = HOOK.read_text(encoding="utf-8")
    assert "Assert-CandidateBranchNaming" in content, "Missing Assert-CandidateBranchNaming function"
    print("PASS: test_hook_contains_naming_function")


def test_naming_blocks_non_candidate():
    content = HOOK.read_text(encoding="utf-8")
    assert "work/candidate-" in content, "Missing candidate naming pattern"
    assert "CANDIDATE BRANCH NAMING VIOLATION" in content, "Missing violation message"
    print("PASS: test_naming_blocks_non_candidate")


def test_naming_allows_candidate():
    content = HOOK.read_text(encoding="utf-8")
    assert "Assert-CandidateBranchNaming" in content
    print("PASS: test_naming_allows_candidate")


def test_canonical_branches_not_affected():
    content = HOOK.read_text(encoding="utf-8")
    assert "Check-CanonicialBranch" in content, "Canonical branch check must be preserved"
    assert "work/canonical-.*" in content, "Canonical pattern must be preserved"
    print("PASS: test_canonical_branches_not_affected")


def test_naming_check_called_in_main_loop():
    content = HOOK.read_text(encoding="utf-8")
    assert "Assert-CandidateBranchNaming" in content
    assert "Check-CanonicialBranch" in content
    assert "continue" in content
    print("PASS: test_naming_check_called_in_main_loop")


def test_naming_allows_canonical_ref_exemption():
    content = HOOK.read_text(encoding="utf-8")
    assert "refs/heads/work/canonical-" in content, "Canonical branches must be exempt from naming check"
    print("PASS: test_naming_allows_canonical_ref_exemption")


if __name__ == "__main__":
    tests = [
        test_hook_exists,
        test_hook_contains_naming_function,
        test_naming_blocks_non_candidate,
        test_naming_allows_candidate,
        test_canonical_branches_not_affected,
        test_naming_check_called_in_main_loop,
        test_naming_allows_canonical_ref_exemption,
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
        exit(1)
