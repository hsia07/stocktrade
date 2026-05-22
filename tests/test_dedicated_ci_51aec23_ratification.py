#!/usr/bin/env python3
"""
Tests for DEDICATED_CI_51AEC23_UNAUTHORIZED_STATE_RATIFICATION candidate package.
"""
import json
import pytest
from pathlib import Path


PKG = Path("automation/control/candidates/DEDICATED_CI_51AEC23_UNAUTHORIZED_STATE_RATIFICATION")


class TestRatification51AEC23Evidence:
    """Test 51aec23 ratification evidence package completeness."""

    def test_evidence_json_exists(self):
        assert (PKG / "evidence.json").exists()

    def test_evidence_json_law_compliance_04(self):
        data = json.loads((PKG / "evidence.json").read_text(encoding="utf-8"))
        assert data.get("law_compliance") == "04"

    def test_evidence_json_accepted_remote_head(self):
        data = json.loads((PKG / "evidence.json").read_text(encoding="utf-8"))
        assert data.get("accepted_remote_head") == "51aec2306d803652786d3a67cff89cf0c781b09c"
        assert data.get("current_local_head") == "51aec2306d803652786d3a67cff89cf0c781b09c"
        assert data.get("current_remote_head") == "51aec2306d803652786d3a67cff89cf0c781b09c"

    def test_evidence_json_user_conditionally_accepted(self):
        data = json.loads((PKG / "evidence.json").read_text(encoding="utf-8"))
        assert data.get("user_conditionally_accepted_remote_state") is True
        assert data.get("rollback_executed") is False

    def test_evidence_json_unauthorized_detected(self):
        data = json.loads((PKG / "evidence.json").read_text(encoding="utf-8"))
        assert data.get("unauthorized_commit_detected") is True
        assert data.get("unauthorized_push_detected") is True
        assert data.get("previous_authorized_head") == "3cb024dbf7131098625419a752587222bbe18f10"

    def test_evidence_json_no_r049_runtime_broker_live(self):
        data = json.loads((PKG / "evidence.json").read_text(encoding="utf-8"))
        assert data.get("r049_started") is not True
        assert data.get("runtime_started") is not True
        assert data.get("broker_api_called") is not True
        assert data.get("order_execution_allowed") is not True

    def test_evidence_json_pre_push_not_user_signoff(self):
        data = json.loads((PKG / "evidence.json").read_text(encoding="utf-8"))
        assert data.get("pre_push_pass_treated_as_user_signoff") is False
        assert data.get("github_actions_pass_treated_as_user_signoff") is False
        assert data.get("github_actions_pending_treated_as_success") is False

    def test_evidence_json_agent_generated_signoff(self):
        data = json.loads((PKG / "evidence.json").read_text(encoding="utf-8"))
        assert data.get("agent_generated_signoff_detected") is True
        assert data.get("agent_generated_signoff_treated_as_user_signoff") is False

    def test_evidence_json_final_recommendation(self):
        data = json.loads((PKG / "evidence.json").read_text(encoding="utf-8"))
        assert data.get("final_recommendation") == "DO_NOT_START_R049"


class TestUserConditionalAcceptanceText:
    """Test user conditional acceptance verbatim text."""

    def test_user_conditional_acceptance_exists(self):
        assert (PKG / "user-conditional-acceptance.txt").exists()

    def test_user_conditional_acceptance_contains_51aec23(self):
        content = (PKG / "user-conditional-acceptance.txt").read_text(encoding="utf-8")
        assert "51aec2306d803652786d3a67cff89cf0c781b09c" in content

    def test_user_conditional_acceptance_contains_no_rollback(self):
        content = (PKG / "user-conditional-acceptance.txt").read_text(encoding="utf-8")
        assert "不立即 rollback" in content or "without immediate rollback" in content.lower()

    def test_user_conditional_acceptance_limits_r049_runtime(self):
        content = (PKG / "user-conditional-acceptance.txt").read_text(encoding="utf-8")
        assert "不得啟動 R049" in content or "R049" in content
        assert "runtime" in content.lower() or "broker" in content.lower()


class TestFixCommitsAuthorizationChain:
    """Test fix commits authorization chain."""

    def test_chain_exists(self):
        assert (PKG / "fix-commits-authorization-chain.json").exists()

    def test_chain_has_11_commits(self):
        data = json.loads((PKG / "fix-commits-authorization-chain.json").read_text(encoding="utf-8"))
        assert data.get("total_commits") == 11

    def test_chain_ratification_commit_authorized(self):
        data = json.loads((PKG / "fix-commits-authorization-chain.json").read_text(encoding="utf-8"))
        ratification = next((c for c in data["commits"] if c["hash"] == "b9edd06e316baeed32a0c58aa3ac9b802f929841"), None)
        assert ratification is not None
        assert ratification.get("user_signoff_exists") is True
        assert ratification.get("signoff_is_real_user") is True
        assert ratification.get("signoff_classification") == "ratified_by_user_condition"

    def test_chain_fix_commits_not_user_authorized(self):
        data = json.loads((PKG / "fix-commits-authorization-chain.json").read_text(encoding="utf-8"))
        fix_commits = [c for c in data["commits"] if c["hash"] != "b9edd06e316baeed32a0c58aa3ac9b802f929841"]
        assert len(fix_commits) == 10
        for c in fix_commits:
            assert c.get("user_signoff_exists") is False
            assert c.get("signoff_classification") == "pre_push_only_not_user_authorized"

    def test_chain_agent_generated_signoff_treated_as_false(self):
        data = json.loads((PKG / "fix-commits-authorization-chain.json").read_text(encoding="utf-8"))
        assert data.get("agent_generated_signoff_treated_as_user_signoff") is False

    def test_chain_pre_push_not_user_signoff(self):
        data = json.loads((PKG / "fix-commits-authorization-chain.json").read_text(encoding="utf-8"))
        assert data.get("pre_push_pass_treated_as_user_signoff") is False

    def test_chain_conditioned_acceptance_not_future_auto_push(self):
        data = json.loads((PKG / "fix-commits-authorization-chain.json").read_text(encoding="utf-8"))
        assert data.get("conditioned_acceptance_used_as_future_auto_push_authorization") is False


class TestGitHubActionsResult:
    """Test GitHub Actions result evidence."""

    def test_github_actions_result_exists(self):
        assert (PKG / "github-actions-result.json").exists()

    def test_github_actions_result_not_verifiable(self):
        data = json.loads((PKG / "github-actions-result.json").read_text(encoding="utf-8"))
        assert data.get("status") == "NOT_VERIFIABLE"
        assert data.get("not_verifiable_reason") is not None

    def test_github_actions_result_not_treated_as_authorization(self):
        data = json.loads((PKG / "github-actions-result.json").read_text(encoding="utf-8"))
        assert data.get("ci_result_treated_as_authorization") is False


class TestRatification51AEC23RequiredFiles:
    """Test all required files exist."""

    def test_required_files_present(self):
        required = ["evidence.json", "candidate.diff", "RETURN_TO_CHATGPT.txt",
                    "test-results.txt", "task.txt", "report.json",
                    "user-conditional-acceptance.txt", "incident-ratification.json",
                    "fix-commits-authorization-chain.json", "github-actions-result.json",
                    "no-aider-used.txt"]
        for f in required:
            assert (PKG / f).exists(), f"Missing: {f}"

    def test_candidate_diff_not_empty(self):
        path = PKG / "candidate.diff"
        assert path.stat().st_size > 0

    def test_candidate_diff_no_bom(self):
        data = (PKG / "candidate.diff").read_bytes()
        assert data[:3] != b"\xef\xbb\xbf"
        assert data[:2] not in (b"\xff\xfe", b"\xfe\xff")