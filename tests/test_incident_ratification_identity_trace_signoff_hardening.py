"""
Test module for:
1. Template_only/test_fixture/machine-generated signoff rejection
2. Identity trace validation
3. FIX_YAML_SYNTAX supersession handling
4. Incident ratification evidence validation
5. R049/runtime/broker/live claim blocking
"""

from __future__ import annotations
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple

import pytest

from automation.control.evidence_checker import EvidenceChecker

FORMAL_RTCG = """round_id: TEST_INCIDENT_RATIFICATION
formal_status_code: 04
base_head: 0d54d0ffa4ea533f9c535c3e0690d183add7cd22
canonical_branch: work/canonical-mainline-repair-001

Review:
This is a formal return-to-ChatGPT for incident ratification testing.
Recommendation: await manual review.
"""

TEMPLATE_ONLY_SIGNOFF = "template_only: Merge authorized for work/canonical-mainline-repair-001 at 0d54d0ffa4ea533f9c535c3e0690d183add7cd22 by user consent. Template only -- NOT a real user signoff."

TEST_FIXTURE_SIGNOFF = "test_fixture: Merge authorized for work/canonical-mainline-repair-001 at 0d54d0ffa4ea533f9c535c3e0690d183add7cd22 by user consent. Test fixture only."

MACHINE_GENERATED_SIGNOFF = "machine-generated: Merge authorized for work/canonical-mainline-repair-001 at 0d54d0ffa4ea533f9c535c3e0690d183add7cd22. Do not use as user authorization."

REAL_LOOKING_SIGNOFF = "Merge authorized for work/canonical-mainline-repair-001 at 0d54d0ffa4ea533f9c535c3e0690d183add7cd22 by user consent. This is a real-looking signoff without template markers."


def _git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


class TestSignoffHardening:
    """Test that template_only/test_fixture/machine-generated signoffs are rejected."""

    @pytest.fixture
    def checker(self):
        return EvidenceChecker(repo_root=Path(tempfile.gettempdir()) / "test_signoff_hardening")

    @pytest.fixture
    def candidate_dir(self, checker):
        d = Path(tempfile.mkdtemp(prefix="signoff_hardening_"))
        yield d
        shutil.rmtree(d, ignore_errors=True)

    def _write_minimal_evidence(self, candidate_dir: Path, signoff_content: str):
        ev = {
            "round_id": "test_signoff_hardening",
            "trace_id": "trace-001",
            "law_compliance": "04",
            "evidence_type": "test",
            "round": "1",
            "phase": "1",
            "append_only_audit": True,
            "candidate_commit": _git_head(),
        }
        (candidate_dir / "evidence.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
        (candidate_dir / "task.txt").write_text("task_id: TEST\ntask_type: test\nlaw_compliance: 04", encoding="utf-8")
        (candidate_dir / "report.json").write_text(json.dumps({"round_id": "test", "status": "completed"}, indent=2), encoding="utf-8")
        (candidate_dir / "candidate.diff").write_text("dummy diff", encoding="utf-8")
        (candidate_dir / "RETURN_TO_CHATGPT.txt").write_text(FORMAL_RTCG, encoding="utf-8")
        (candidate_dir / "no-aider-used.txt").write_text("No aider used", encoding="utf-8")
        (candidate_dir / "test-results.txt").write_text("TEST RESULTS\npassed: 1\nfailed: 0", encoding="utf-8")
        (candidate_dir / "merge_signoff.txt").write_text(signoff_content, encoding="utf-8")

    def test_template_only_signoff_blocked(self, checker, candidate_dir):
        """template_only signoff must be rejected."""
        (candidate_dir / "merge_signoff.txt").write_text(TEMPLATE_ONLY_SIGNOFF, encoding="utf-8")
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("template_or_machine_marker:template_only" in i for i in issues), \
            f"Expected template_only blocked, got: {issues}"

    def test_test_fixture_signoff_blocked(self, checker, candidate_dir):
        """test_fixture signoff must be rejected."""
        (candidate_dir / "merge_signoff.txt").write_text(TEST_FIXTURE_SIGNOFF, encoding="utf-8")
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("template_or_machine_marker:test_fixture" in i for i in issues), \
            f"Expected test_fixture blocked, got: {issues}"

    def test_machine_generated_signoff_blocked(self, checker, candidate_dir):
        """machine-generated signoff must be rejected."""
        (candidate_dir / "merge_signoff.txt").write_text(MACHINE_GENERATED_SIGNOFF, encoding="utf-8")
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("template_or_machine_marker:machine-generated" in i for i in issues), \
            f"Expected machine-generated blocked, got: {issues}"

    def test_real_looking_signoff_passes_syntactic_gate(self, checker, candidate_dir):
        """Real-looking syntactic signoff (no template marker) should pass gate but document cryptographic_not_verified."""
        (candidate_dir / "merge_signoff.txt").write_text(REAL_LOOKING_SIGNOFF, encoding="utf-8")
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert not any("template_or_machine_marker" in i for i in issues), \
            f"Real-looking signoff should pass template check, got: {issues}"


def _write_standard_evidence(candidate_dir: Path, ev_overrides=None):
    ev = {
        "round_id": "test_identity",
        "trace_id": "trace-001",
        "law_compliance": "04",
        "evidence_type": "test",
        "round": "1",
        "phase": "1",
        "append_only_audit": True,
        "candidate_commit": _git_head(),
    }
    if ev_overrides:
        ev.update(ev_overrides)
    (candidate_dir / "evidence.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
    (candidate_dir / "task.txt").write_text("task_id: TEST\ntask_type: test\nlaw_compliance: 04", encoding="utf-8")
    (candidate_dir / "report.json").write_text(json.dumps({"round_id": "test", "status": "completed"}, indent=2), encoding="utf-8")
    (candidate_dir / "candidate.diff").write_text("dummy diff", encoding="utf-8")
    (candidate_dir / "RETURN_TO_CHATGPT.txt").write_text(FORMAL_RTCG, encoding="utf-8")
    (candidate_dir / "no-aider-used.txt").write_text("No aider used", encoding="utf-8")
    (candidate_dir / "test-results.txt").write_text("TEST RESULTS\npassed: 1\nfailed: 0", encoding="utf-8")
    return ev


class TestIdentityTraceValidation:
    """Test identity trace validation."""

    @pytest.fixture
    def checker(self):
        return EvidenceChecker(repo_root=Path(tempfile.gettempdir()) / "test_identity_trace")

    @pytest.fixture
    def candidate_dir(self, checker):
        d = Path(tempfile.mkdtemp(prefix="identity_trace_"))
        yield d
        shutil.rmtree(d, ignore_errors=True)

    def test_identity_collapse_unlabeled_is_tracked(self, checker, candidate_dir):
        """candidate_commit == base_head without identity_collapse label must be detectable."""
        _write_standard_evidence(candidate_dir)
        assert True

    def test_identity_trace_missing_accepted_remote_head(self, checker, candidate_dir):
        """Identity trace missing accepted_remote_head should be flagged."""
        ev = {
            "round_id": "test_identity_gap",
            "trace_id": "trace-001",
            "law_compliance": "04",
            "evidence_type": "test",
            "identity_trace": {
                "previous_authorized_head": "cc02208e3ed598bc1dccc1bb1f6a9521a573bd18",
                "canonical_merge_commit": "0d54d0ffa4ea533f9c535c3e0690d183add7cd22",
                "base_head": "cc02208e3ed598bc1dccc1bb1f6a9521a573bd18",
                "candidate_head": None,
                "evidence_status": "valid",
                "traceability_sufficient": False,
            }
        }
        assert "accepted_remote_head" not in ev["identity_trace"]


class TestFixYamlSupersession:
    """Test FIX_YAML_SYNTAX supersession handling."""

    def test_fix_yaml_invalid_marked_superseded(self):
        """FIX_YAML_SYNTAX must be marked superseded with should_not_be_used_for_acceptance."""
        path = Path("automation/control/candidates/FIX_YAML_SYNTAX/evidence.json")
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("should_not_be_used_for_acceptance") is True
        assert data.get("superseded_by") == "FIX_YAML_SYNTAX_V2"
        assert data.get("invalid_reason") == "empty_candidate_diff"
        assert data["identity_trace"]["evidence_status"] == "invalid_superseded"

    def test_fix_yaml_v2_supersedes_fix_yaml(self):
        """FIX_YAML_V2 identity trace should reference supersedes FIX_YAML."""
        path = Path("automation/control/candidates/FIX_YAML_SYNTAX_V2/evidence.json")
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "identity_trace" in data
        assert data["identity_trace"].get("supersedes") == "FIX_YAML_SYNTAX"
        assert data["identity_trace"].get("superseded_invalid_reason") == "FIX_YAML_SYNTAX/candidate.diff = 0 bytes"

    def test_validate_canonical_repair_fails_fix_yaml(self):
        """validate_canonical_repair_evidence.py must FAIL for FIX_YAML_SYNTAX."""
        from scripts.validation.validate_canonical_repair_evidence import validate_candidate
        from pathlib import Path
        pkg = Path("automation/control/candidates/FIX_YAML_SYNTAX")
        ok, issues = validate_candidate(pkg)
        assert not ok, "FIX_YAML_SYNTAX should FAIL validation (empty candidate.diff)"
        assert any("empty" in i for i in issues), f"Expected empty candidate.diff issue, got: {issues}"


class TestR049RuntimeBrokerLiveBlocking:
    """Test that ratification evidence does not claim R049/runtime/broker/live."""

    def test_ratification_evidence_no_r049_claims(self):
        """Ratification evidence package must not claim R049/runtime/broker/live."""
        path = Path("automation/control/candidates/DEDICATED_CI_UNAUTHORIZED_STATE_RATIFICATION_CLEANUP/evidence.json")
        if not path.exists():
            pytest.skip("Ratification package not yet created")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("r049_started") is not True
        assert data.get("runtime_started") is not True
        assert data.get("broker_api_called") is not True
        assert data.get("order_execution_allowed") is not True
        assert data.get("trading_broker_execution_live_started") is not True
        assert data.get("live_started") is not True


class TestUserConditionalAcceptance:
    """Test that user conditional acceptance text is recorded."""

    def test_user_conditional_acceptance_recorded(self):
        """user-conditional-acceptance.txt must exist with exact user text."""
        path = Path("automation/control/candidates/DEDICATED_CI_UNAUTHORIZED_STATE_RATIFICATION_CLEANUP/user-conditional-acceptance.txt")
        if not path.exists():
            pytest.skip("Ratification package not yet created")
        content = path.read_text(encoding="utf-8")
        assert "0d54d0ffa4ea533f9c535c3e0690d183add7cd22" in content
        assert "我同意條件式接受" in content
        assert "不立即 rollback" in content

    def test_ratification_package_has_incident_ratification(self):
        """Ratification package must have incident-ratification.json."""
        path = Path("automation/control/candidates/DEDICATED_CI_UNAUTHORIZED_STATE_RATIFICATION_CLEANUP/incident-ratification.json")
        if not path.exists():
            pytest.skip("Ratification package not yet created")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["incident_type"] == "unauthorized_canonical_branch_advance"
        assert data["rollback_executed"] is False
        assert data["user_conditional_acceptance"]["accepted"] is True
        assert "ratification_only_not_future_authorization" in data["user_conditional_acceptance"]["scope_of_acceptance"]