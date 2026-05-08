"""
Tests for evidence_checker.py indentation fix.
Verifies file parses, class imports, and orphaned methods are restored.
"""

import sys
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
EVIDENCE_CHECKER_PATH = REPO_ROOT / "automation" / "control" / "evidence_checker.py"


def test_evidence_checker_parses():
    source = EVIDENCE_CHECKER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    print("PASS: test_evidence_checker_parses")


def test_evidence_checker_imports():
    source = EVIDENCE_CHECKER_PATH.read_text(encoding="utf-8")
    assert "from .return_to_chatgpt_verifier import ReturnToChatGPTVerifier" in source
    # Verify import is near top (before class definition)
    import_pos = source.index("from .return_to_chatgpt_verifier import ReturnToChatGPTVerifier")
    class_pos = source.index("class EvidenceChecker")
    assert import_pos < class_pos, "Import must be before class definition"
    print("PASS: test_evidence_checker_imports")


def test_orphaned_methods_restored():
    source = EVIDENCE_CHECKER_PATH.read_text(encoding="utf-8")
    # Verify both methods exist inside class (preceded by 4-space indent)
    assert "    def verify_return_to_chatgpt" in source
    assert "    def validate_return_to_chatgpt_in_evidence" in source
    # Verify no module-level orphaned methods (no import between class methods)
    assert "from .return_to_chatgpt_verifier" not in source[source.index("class EvidenceChecker"):source.rindex("    def ")]
    print("PASS: test_orphaned_methods_restored")


def test_no_orphaned_code_outside_class():
    source = EVIDENCE_CHECKER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert any(c.name == "EvidenceChecker" for c in classes)
    print("PASS: test_no_orphaned_code_outside_class")


def test_auto_advance_imports():
    """Verify the downstream consumer imports correctly."""
    sys.path.insert(0, str(REPO_ROOT))
    from automation.control.auto_advance import AutoAdvanceController
    ctrl = AutoAdvanceController(REPO_ROOT)
    assert ctrl.AUTO_CANDIDATE_READY == "auto_candidate_ready"
    assert ctrl.is_auto_candidate_status("auto_candidate_ready") is True
    assert ctrl.is_auto_candidate_status("blocked") is False
    print("PASS: test_auto_advance_imports")


if __name__ == "__main__":
    tests = [
        test_evidence_checker_parses,
        test_evidence_checker_imports,
        test_orphaned_methods_restored,
        test_no_orphaned_code_outside_class,
        test_auto_advance_imports,
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
