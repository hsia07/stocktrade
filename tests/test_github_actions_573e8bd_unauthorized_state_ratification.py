#!/usr/bin/env python3
"""
Tests for GITHUB_ACTIONS_573E8BD_UNAUTHORIZED_STATE_RATIFICATION.
"""
import json, pytest
from pathlib import Path


class TestGitHubActions573e8bdRatification:
    """Test 573e8bd ratification package completeness and anti-recurrence governance."""

    def test_573e8bd_ratification_package_exists(self):
        """573e8bd ratification package exists."""
        pkg = Path("automation/control/candidates/GITHUB_ACTIONS_573E8BD_UNAUTHORIZED_STATE_RATIFICATION")
        assert pkg.exists(), "Ratification package should exist"

    def test_573e8bd_ratification_evidence_json_valid(self):
        """573e8bd ratification evidence.json is valid."""
        pkg = Path("automation/control/candidates/GITHUB_ACTIONS_573E8BD_UNAUTHORIZED_STATE_RATIFICATION")
        evidence = json.loads((pkg / "evidence.json").read_text(encoding="utf-8"))
        assert evidence.get("law_compliance") == "04"
        assert evidence.get("user_conditionally_accepted_remote_state") is True
        assert evidence.get("accepted_remote_head") == "573e8bd92677186e04f30653f04fd581f7b5e4be"
        assert evidence.get("previous_authorized_head") == "ad529dea42b91b546b764afd56a00cb89eb74e51"
        assert evidence.get("unauthorized_commit_detected") is True
        assert evidence.get("unauthorized_merge_detected") is True
        assert evidence.get("unauthorized_push_detected") is True
        assert evidence.get("rollback_executed") is False
        assert evidence.get("r049_started") is False
        assert evidence.get("runtime_started") is False
        assert evidence.get("order_execution_allowed") is False

    def test_573e8bd_ratification_user_conditional_acceptance_recorded(self):
        """User conditional acceptance text is recorded verbatim."""
        pkg = Path("automation/control/candidates/GITHUB_ACTIONS_573E8BD_UNAUTHORIZED_STATE_RATIFICATION")
        txt = (pkg / "user-conditional-acceptance.txt").read_text(encoding="utf-8")
        assert "573e8bd92677186e04f30653f04fd581f7b5e4be" in txt
        assert "不立即 rollback" in txt
        assert "不得啟動 R049" in txt
        assert len(txt) > 50, "Acceptance text must be verbatim and non-trivial"

    def test_573e8bd_authorization_chain_complete(self):
        """Authorization chain includes both commits 8046385 and 573e8bd."""
        pkg = Path("automation/control/candidates/GITHUB_ACTIONS_573E8BD_UNAUTHORIZED_STATE_RATIFICATION")
        chain = json.loads((pkg / "authorization-chain.json").read_text(encoding="utf-8"))
        hashes = [c["commit_hash"] for c in chain]
        assert "804638568127de0d9b4268b69cae50cba8beb9a4" in hashes
        assert "573e8bd92677186e04f30653f04fd581f7b5e4be" in hashes
        for c in chain:
            assert c["user_manual_review_signoff_exists"] is False
            assert c["user_merge_signoff_exists"] is False
            assert c["user_push_signoff_exists"] is False
            assert c["governance_classification"] == "unauthorized_but_conditionally_accepted"

    def test_tests_pass_not_treated_as_user_signoff(self):
        """Tests pass must not be treated as user signoff."""
        from pathlib import Path
        src = Path("automation/control/evidence_checker.py").read_text(encoding="utf-8")
        lines = src.splitlines()
        for i, line in enumerate(lines):
            lower = line.lower()
            if "test" in lower and "signoff" in lower and "user" in lower:
                pytest.fail(f"evidence_checker.py line {i+1}: tests should not be conflated with user signoff: {line.strip()}")

    def test_pre_push_pass_not_treated_as_user_signoff(self):
        """Pre-push PASS must not be treated as user signoff."""
        from pathlib import Path
        src = Path("automation/control/evidence_checker.py").read_text(encoding="utf-8")
        lower = src.lower()
        combined = lower.replace("pre_push", "").replace("pre-push", "")
        if "pre_push_pass_as_user_signoff" in combined or "prepush_pass_as_user_signoff" in combined:
            pytest.fail("evidence_checker.py: pre-push pass must not be treated as user signoff")

    def test_github_actions_not_verifiable_not_claimed_as_success(self):
        """GitHub Actions NOT_VERIFIABLE must not be claimed as success."""
        from pathlib import Path
        src = Path("automation/control/evidence_checker.py").read_text(encoding="utf-8")
        lower = src.lower()
        if "not_verifiable" in lower and "success" in lower and "claimed" not in lower:
            for i, line in enumerate(src.splitlines()):
                if "not_verifiable" in line.lower() and ("success" in line.lower() and "false" not in line.lower() and "not" not in line.lower()):
                    if "github_actions" in line.lower() or "ci" in line.lower():
                        pytest.fail(f"evidence_checker.py line {i+1}: GitHub Actions NOT_VERIFIABLE should not be claimed as success: {line.strip()}")

    def test_conditional_acceptance_not_future_auto_push_authorization(self):
        """User conditional acceptance must not be used as future auto-push authorization."""
        from pathlib import Path
        src = Path("automation/control/evidence_checker.py").read_text(encoding="utf-8")
        lower = src.lower()
        if "future" in lower and "auto" in lower and "push" in lower and "authorization" in lower:
            pytest.fail("evidence_checker.py: conditional acceptance must not be used as future auto-push authorization")

    def test_normal_governance_signoff_gate_preserved(self):
        """Normal governance package missing merge_signoff/push_signoff must still fail."""
        from automation.control.evidence_checker import EvidenceChecker
        pkg = Path("automation/control/candidates/FIX_YAML_SYNTAX")
        checker = EvidenceChecker(repo_root=Path(".").resolve())
        ok, issues = checker.check_completeness(pkg)
        assert not ok, "Normal governance package without signoff should FAIL"
        assert any("no_authorization" in i or "template" in i for i in issues), f"Expected auth/template issue, got: {issues}"

    def test_573e8bd_ratification_package_passes_evidence_checker(self):
        """573e8bd ratification package passes evidence_checker."""
        from automation.control.evidence_checker import EvidenceChecker
        pkg = Path("automation/control/candidates/GITHUB_ACTIONS_573E8BD_UNAUTHORIZED_STATE_RATIFICATION")
        checker = EvidenceChecker(repo_root=Path(".").resolve())
        ok, issues = checker.check_completeness(pkg)
        assert ok, f"573e8bd ratification should pass evidence_checker, got: {issues}"

    def test_syntactic_only_gap_documented(self):
        """Signoff validation syntactic-only gap is documented."""
        from pathlib import Path
        src = Path("automation/control/evidence_checker.py").read_text(encoding="utf-8")
        lower = src.lower()
        assert "syntactic" in lower, "evidence_checker.py should document syntactic-only gap"
        assert "not cryptographic" in lower or "cryptographic" in lower, "evidence_checker.py should reference cryptographic verification gap"