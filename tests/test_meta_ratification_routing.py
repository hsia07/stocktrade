#!/usr/bin/env python3
"""
Tests for meta-ratification evidence routing in evidence_checker.py.
"""
import json, pytest
from pathlib import Path


class TestMetaRatificationRouting:
    """Test that meta-ratification packages are handled correctly."""

    def test_meta_ratification_package_passes_without_merge_signoff(self):
        """Meta-ratification package with user-conditional-acceptance.txt passes without merge_signoff.txt."""
        from automation.control.evidence_checker import EvidenceChecker
        pkg = Path("automation/control/candidates/DEDICATED_CI_51AEC23_UNAUTHORIZED_STATE_RATIFICATION")
        assert pkg.exists()
        checker = EvidenceChecker(repo_root=Path(".").resolve())
        ok, issues = checker.check_completeness(pkg)
        assert ok, f"Meta-ratification should pass, got: {issues}"

    def test_meta_ratification_requires_user_conditional_acceptance(self):
        """Meta-ratification detection requires user-conditional-acceptance.txt existence."""
        from automation.control.evidence_checker import EvidenceChecker
        import inspect
        src = inspect.getsource(EvidenceChecker._check_governance_authorization_gate)
        assert "user_conditionally_accepted_remote_state" in src
        assert "accepted_remote_head" in src
        assert "user-conditional-acceptance.txt" in src

    def test_meta_ratification_still_blocks_order_execution_allowed(self):
        """Meta-ratification packages with order_execution_allowed=true still fail."""
        from automation.control.evidence_checker import EvidenceChecker
        from pathlib import Path
        import tempfile, shutil

        pkg = Path(tempfile.mkdtemp()) / "test_meta_blocked"
        pkg.mkdir(parents=True)
        (pkg / "evidence.json").write_text(json.dumps({
            "law_compliance": "04",
            "round_id": "test_meta_ratification_unauthorized_state_candidate",
            "task_type": "governance_ratification",
            "evidence_type": "unauthorized_state_ratification",
            "user_conditionally_accepted_remote_state": True,
            "accepted_remote_head": "abc123def",
            "order_execution_allowed": True,
        }), encoding="utf-8")
        (pkg / "user-conditional-acceptance.txt").write_text(
            "user conditionally accepted remote state", encoding="utf-8"
        )
        (pkg / "task.txt").write_text("test task", encoding="utf-8")
        (pkg / "report.json").write_text(json.dumps({
            "summary": "test",
            "status": "completed",
            "round_id": "test_meta_ratification_unauthorized_state_candidate",
            "changes": [],
            "test_count": 1,
            "tests_passed": 1,
        }), encoding="utf-8")
        (pkg / "candidate.diff").write_text("diff content", encoding="utf-8")
        (pkg / "no-aider-used.txt").write_text("no aider used", encoding="utf-8")
        (pkg / "test-results.txt").write_text("all pass", encoding="utf-8")
        (pkg / "RETURN_TO_CHATGPT.txt").write_text("x" * 200, encoding="utf-8")
        checker = EvidenceChecker(repo_root=Path(".").resolve())
        ok, issues = checker.check_completeness(pkg)
        shutil.rmtree(pkg.parent)
        assert not ok, f"Meta-ratification with order_execution_allowed=true should FAIL, got: {issues}"
        block_issues = [i for i in issues if "order_execution_allowed" in i or "meta_ratification_blocked" in i]
        assert len(block_issues) > 0, f"Expected order_execution_allowed/meta_ratification_blocked in issues, got: {issues}"

    def test_meta_ratification_blocks_r049_claims(self):
        """Meta-ratification packages claiming R049 still fail."""
        from automation.control.evidence_checker import EvidenceChecker
        from pathlib import Path
        import tempfile, shutil

        pkg = Path(tempfile.mkdtemp()) / "test_meta_r049"
        pkg.mkdir(parents=True)
        (pkg / "evidence.json").write_text(json.dumps({
            "law_compliance": "04",
            "round_id": "test_meta_ratification_unauthorized_state_candidate",
            "task_type": "governance_ratification",
            "evidence_type": "unauthorized_state_ratification",
            "user_conditionally_accepted_remote_state": True,
            "accepted_remote_head": "abc123def",
            "r049_started": True,
        }), encoding="utf-8")
        (pkg / "user-conditional-acceptance.txt").write_text(
            "user conditionally accepted remote state", encoding="utf-8"
        )
        (pkg / "task.txt").write_text("test task", encoding="utf-8")
        (pkg / "report.json").write_text(json.dumps({
            "summary": "test",
            "status": "completed",
            "round_id": "test_meta_ratification_unauthorized_state_candidate",
            "changes": [],
            "test_count": 1,
            "tests_passed": 1,
        }), encoding="utf-8")
        (pkg / "candidate.diff").write_text("diff content", encoding="utf-8")
        (pkg / "no-aider-used.txt").write_text("no aider used", encoding="utf-8")
        (pkg / "test-results.txt").write_text("all pass", encoding="utf-8")
        (pkg / "RETURN_TO_CHATGPT.txt").write_text("x" * 200, encoding="utf-8")
        checker = EvidenceChecker(repo_root=Path(".").resolve())
        ok, issues = checker.check_completeness(pkg)
        shutil.rmtree(pkg.parent)
        assert not ok, f"Meta-ratification claiming R049 should FAIL, got: {issues}"
        block_issues = [i for i in issues if "r049" in i or "meta_ratification_blocked" in i]
        assert len(block_issues) > 0, f"Expected r049/meta_ratification_blocked in issues, got: {issues}"

    def test_normal_governance_package_still_requires_signoff(self):
        """Normal governance package without signoff still fails."""
        from automation.control.evidence_checker import EvidenceChecker
        pkg = Path("automation/control/candidates/FIX_YAML_SYNTAX")
        checker = EvidenceChecker(repo_root=Path(".").resolve())
        ok, issues = checker.check_completeness(pkg)
        assert not ok, "Normal governance package without signoff should FAIL"
        assert any("no_authorization" in i or "template" in i for i in issues), f"Expected auth/template issue, got: {issues}"

    def test_ratification_cleanup_still_passes(self):
        """RATIFICATION_CLEANUP package (has merge_signoff + push_signoff) continues to pass."""
        from automation.control.evidence_checker import EvidenceChecker
        pkg = Path("automation/control/candidates/DEDICATED_CI_UNAUTHORIZED_STATE_RATIFICATION_CLEANUP")
        checker = EvidenceChecker(repo_root=Path(".").resolve())
        ok, issues = checker.check_completeness(pkg)
        assert ok, f"RATIFICATION_CLEANUP should pass, got: {issues}"

    def test_meta_ratification_not_used_as_future_auto_push_authorization(self):
        """Meta-ratification routing does not use conditional acceptance as future auto-push auth."""
        from pathlib import Path
        src = Path("automation/control/evidence_checker.py").read_text(encoding="utf-8")
        assert "future_auto_push" not in src.lower(), "Evidence checker should not reference future auto-push authorization"

    def test_check_evidence_package_script_passes_on_meta_ratification(self):
        """check_evidence_package.py script passes on DEDICATED_CI_51AEC23."""
        from scripts.validation.check_evidence_package import main as check_main
        import sys
        old_argv = sys.argv
        try:
            sys.argv = ["check", "automation/control/candidates/DEDICATED_CI_51AEC23_UNAUTHORIZED_STATE_RATIFICATION"]
            ok = True
            try:
                check_main()
            except SystemExit as e:
                if e.code != 0:
                    ok = False
            assert ok, "check_evidence_package.py should PASS on meta-ratification"
        finally:
            sys.argv = old_argv