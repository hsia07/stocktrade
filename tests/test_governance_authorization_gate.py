import pytest
import json
from pathlib import Path
import tempfile
import shutil


from automation.control.evidence_checker import EvidenceChecker


VALID_MERGE_SIGNOFF = (
    "Merge authorized for work/canonical-mainline-repair-001 "
    "at 904f4604b85800194725ad3fe8abd3ee71ec45a9 by user consent"
)
VALID_PUSH_SIGNOFF = (
    "Push authorized for work/canonical-mainline-repair-001 "
    "at 904f4604b85800194725ad3fe8abd3ee71ec45a9 by user consent"
)
CANONICAL_HASH = "904f4604b85800194725ad3fe8abd3ee71ec45a9"

FORMAL_RTCG = (
    "round_id: GOVERNANCE_PREVENTION_GATE_TEST\n"
    "formal_status_code: test\n"
    "base_head: 904f4604b85800194725ad3fe8abd3ee71ec45a9\n"
    "candidate_branch: test\n"
    "candidate_commit: test\n"
    "recommendation: test candidate\n"
    "remaining blockers: none\n"
)

SUMMARY_ONLY_RTCG = "This is just a short summary without formal fields."


def _write_standard_evidence(candidate_dir, evidence_overrides=None):
    """Create standard evidence files in candidate_dir. Returns evidence dict."""
    ev = {
        "round_id": "test", "trace_id": "trace-001",
        "law_compliance": "04", "evidence_type": "test",
        "round": "1", "phase": "1", "append_only_audit": True,
        "candidate_commit": CANONICAL_HASH,
    }
    if evidence_overrides:
        ev.update(evidence_overrides)
    (candidate_dir / "evidence.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
    (candidate_dir / "task.txt").write_text(
        "task_id: TEST\ntask_type: test\nphase: 1\nlaw_compliance: 04\nseverity: medium",
        encoding="utf-8",
    )
    (candidate_dir / "report.json").write_text(json.dumps({
        "round_id": "test", "status": "completed",
        "canonical_branch": "origin/work/canonical-mainline-repair-001",
        "canonical_head": CANONICAL_HASH,
        "test_count": 1, "tests_passed": 1,
    }, indent=2), encoding="utf-8")
    (candidate_dir / "candidate.diff").write_text("dummy diff", encoding="utf-8")
    (candidate_dir / "no-aider-used.txt").write_text("No aider used", encoding="utf-8")
    (candidate_dir / "test-results.txt").write_text("TEST RESULTS\npassed: 1\nfailed: 0", encoding="utf-8")
    return ev


class TestGovernanceAuthorizationGate:
    """Tests for _check_governance_authorization_gate (Law 04 Chapter 22)."""

    @pytest.fixture
    def checker(self):
        return EvidenceChecker(repo_root=Path(tempfile.gettempdir()) / "test_gov_gate")

    @pytest.fixture
    def candidate_dir(self, checker):
        d = Path(tempfile.mkdtemp(prefix="gov_candidate_"))
        yield d
        shutil.rmtree(d, ignore_errors=True)

    def _write_evidence(self, candidate_dir: Path, evidence: dict):
        (candidate_dir / "evidence.json").write_text(
            json.dumps(evidence, indent=2), encoding="utf-8"
        )

    # --- Governance gate applicability (_is_governance_candidate) ---

    def test_non_governance_candidate_not_blocked_by_gate(self, checker, candidate_dir):
        """Non-governance round should NOT trigger governance signoff gate."""
        ev = _write_standard_evidence(candidate_dir, {
            "round_id": "R031_test",  # NOT a governance trigger word
        })
        (candidate_dir / "RETURN_TO_CHATGPT.txt").write_text(FORMAL_RTCG, encoding="utf-8")
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")

        assert not checker._is_governance_candidate(ev)
        complete, missing = checker.check_completeness(candidate_dir)
        assert complete, f"Non-governance candidate should pass, got missing: {missing}"
        assert not any("governance_gate" in m for m in missing)

    def test_governance_trigger_by_keyword(self, checker, candidate_dir):
        """governance keyword in round_id triggers gate."""
        ev = _write_standard_evidence(candidate_dir, {"round_id": "governance_test"})
        assert checker._is_governance_candidate(ev)

    def test_governance_trigger_by_requires_flag(self, checker, candidate_dir):
        """requires_authorization_gate=true triggers gate."""
        ev = _write_standard_evidence(candidate_dir, {"requires_authorization_gate": True})
        assert checker._is_governance_candidate(ev)

    def test_governance_trigger_by_round_keyword_rework(self, checker, candidate_dir):
        """rework keyword triggers gate."""
        ev = _write_standard_evidence(candidate_dir, {"round_id": "test_rework"})
        assert checker._is_governance_candidate(ev)

    # --- RETURN_TO_CHATGPT.txt checks ---

    def test_missing_return_to_chatgpt_fails(self, checker, candidate_dir):
        """Missing RETURN_TO_CHATGPT.txt should fail."""
        _write_standard_evidence(candidate_dir, {
            "round_id": "governance_test", "requires_authorization_gate": True,
        })
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")
        complete, missing = checker.check_completeness(candidate_dir)
        assert not complete
        assert any("missing:RETURN_TO_CHATGPT.txt" in m for m in missing)

    def test_summary_only_return_to_chatgpt_fails(self, checker, candidate_dir):
        """Summary-only RETURN_TO_CHATGPT.txt content should fail."""
        _write_standard_evidence(candidate_dir, {
            "round_id": "governance_test", "requires_authorization_gate": True,
        })
        (candidate_dir / "RETURN_TO_CHATGPT.txt").write_text(SUMMARY_ONLY_RTCG, encoding="utf-8")
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")
        complete, missing = checker.check_completeness(candidate_dir)
        assert not complete
        assert any("evidence_invalid:return_to_chatgpt_formal_body" in m for m in missing)

    def test_formal_return_to_chatgpt_passes(self, checker, candidate_dir):
        """Formal RETURN_TO_CHATGPT.txt should pass validation (non-governance candidate)."""
        _write_standard_evidence(candidate_dir, {
            "round_id": "R031_test",  # NOT a governance trigger
        })
        (candidate_dir / "RETURN_TO_CHATGPT.txt").write_text(FORMAL_RTCG, encoding="utf-8")
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")
        complete, missing = checker.check_completeness(candidate_dir)
        assert complete, f"Expected complete, got missing: {missing}"

    # --- No signoff files (governance candidate only) ---

    def test_no_signoff_files_blocked_for_governance(self, checker, candidate_dir):
        """Governance candidate without signoff files should be blocked."""
        ev = _write_standard_evidence(candidate_dir, {
            "round_id": "governance_test", "requires_authorization_gate": True,
        })
        (candidate_dir / "RETURN_TO_CHATGPT.txt").write_text(FORMAL_RTCG, encoding="utf-8")
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")
        issues = checker._check_governance_authorization_gate(ev, candidate_dir)
        assert any("governance_gate:no_authorization_files_found" in i for i in issues)

    def test_governance_candidate_without_signoff_fails_check_completeness(self, checker, candidate_dir):
        """Governance candidate via check_completeness without signoff should fail."""
        _write_standard_evidence(candidate_dir, {
            "round_id": "governance_test", "requires_authorization_gate": True,
        })
        (candidate_dir / "RETURN_TO_CHATGPT.txt").write_text(FORMAL_RTCG, encoding="utf-8")
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")
        complete, missing = checker.check_completeness(candidate_dir)
        assert not complete
        assert any("governance_gate:no_authorization_files_found" in m for m in missing)

    # --- Valid signoffs ---

    def test_merge_signoff_valid_passes(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(VALID_MERGE_SIGNOFF, encoding="utf-8")
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert not any(i.startswith("governance_gate:") for i in issues)

    def test_push_signoff_valid_passes(self, checker, candidate_dir):
        (candidate_dir / "push_signoff.txt").write_text(VALID_PUSH_SIGNOFF, encoding="utf-8")
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert not any(i.startswith("governance_gate:") for i in issues)

    def test_both_signoffs_valid_passes(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(VALID_MERGE_SIGNOFF, encoding="utf-8")
        (candidate_dir / "push_signoff.txt").write_text(VALID_PUSH_SIGNOFF, encoding="utf-8")
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert not any(i.startswith("governance_gate:") for i in issues)

    # --- Too short ---

    def test_merge_signoff_too_short(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text("ok", encoding="utf-8")
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:merge_signoff_too_short" in i for i in issues)

    def test_push_signoff_too_short(self, checker, candidate_dir):
        (candidate_dir / "push_signoff.txt").write_text("no", encoding="utf-8")
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:push_signoff_too_short" in i for i in issues)

    # --- Missing authorization text ---

    def test_merge_signoff_missing_auth_text(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(
            "merge for work/canonical-mainline-repair-001 "
            "at 904f4604b85800194725ad3fe8abd3ee71ec45a9 no auth"
        )
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:merge_signoff_missing_authorization_text" in i for i in issues)

    def test_push_signoff_missing_auth_text(self, checker, candidate_dir):
        (candidate_dir / "push_signoff.txt").write_text(
            "push for work/canonical-mainline-repair-001 "
            "at 904f4604b85800194725ad3fe8abd3ee71ec45a9 no auth"
        )
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:push_signoff_missing_authorization_text" in i for i in issues)

    # --- Empty file ---

    def test_empty_file_treated_as_missing(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text("", encoding="utf-8")
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:no_authorization_files_found" in i for i in issues)

    # --- Missing action type ---

    def test_merge_signoff_missing_action_type(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(
            "Authorized for work/canonical-mainline-repair-001 "
            "at 904f4604b85800194725ad3fe8abd3ee71ec45a9 consent"
        )
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:merge_signoff_missing_action_type" in i for i in issues)

    def test_push_signoff_missing_action_type(self, checker, candidate_dir):
        (candidate_dir / "push_signoff.txt").write_text(
            "Authorized for work/canonical-mainline-repair-001 "
            "at 904f4604b85800194725ad3fe8abd3ee71ec45a9 consent"
        )
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:push_signoff_missing_action_type" in i for i in issues)

    # --- Missing target branch ---

    def test_merge_signoff_missing_branch(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(
            "Merge authorized at 904f4604b85800194725ad3fe8abd3ee71ec45a9 consent"
        )
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:merge_signoff_missing_target_branch" in i for i in issues)

    def test_push_signoff_missing_branch(self, checker, candidate_dir):
        (candidate_dir / "push_signoff.txt").write_text(
            "Push authorized at 904f4604b85800194725ad3fe8abd3ee71ec45a9 consent"
        )
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:push_signoff_missing_target_branch" in i for i in issues)

    # --- Missing hash ---

    def test_merge_signoff_missing_hash(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(
            "Merge authorized for work/canonical-mainline-repair-001 by consent"
        )
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:merge_signoff_missing_hash" in i for i in issues)

    def test_push_signoff_missing_hash(self, checker, candidate_dir):
        (candidate_dir / "push_signoff.txt").write_text(
            "Push authorized for work/canonical-mainline-repair-001 by consent"
        )
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:push_signoff_missing_hash" in i for i in issues)

    # --- Incomplete evidence ---

    def test_incomplete_evidence_missing_candidate_diff(self, checker, candidate_dir):
        _write_standard_evidence(candidate_dir, {"round_id": "test"})
        (candidate_dir / "RETURN_TO_CHATGPT.txt").write_text(FORMAL_RTCG, encoding="utf-8")
        (candidate_dir / "candidate.diff").unlink(missing_ok=True)
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")
        complete, missing = checker.check_completeness(candidate_dir)
        assert not complete
        assert any("missing:candidate.diff" in m for m in missing)

    def test_incomplete_evidence_missing_test_results(self, checker, candidate_dir):
        _write_standard_evidence(candidate_dir, {"round_id": "test"})
        (candidate_dir / "RETURN_TO_CHATGPT.txt").write_text(FORMAL_RTCG, encoding="utf-8")
        (candidate_dir / "test-results.txt").unlink(missing_ok=True)
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")
        complete, missing = checker.check_completeness(candidate_dir)
        assert not complete
        assert any("missing:test-results.txt" in m for m in missing)

    def test_incomplete_evidence_missing_evidence_json(self, checker, candidate_dir):
        _write_standard_evidence(candidate_dir, {"round_id": "test"})
        (candidate_dir / "RETURN_TO_CHATGPT.txt").write_text(FORMAL_RTCG, encoding="utf-8")
        (candidate_dir / "evidence.json").unlink(missing_ok=True)
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")
        complete, missing = checker.check_completeness(candidate_dir)
        assert not complete
        assert any("missing:evidence.json" in m for m in missing)

    # --- Positive authorized complete case ---

    def test_authorized_governance_complete_passes(self, checker, candidate_dir):
        """Full governance candidate with all evidence + signoffs should pass."""
        _write_standard_evidence(candidate_dir, {
            "round_id": "governance_prevention_gate_test",
            "requires_authorization_gate": True,
        })
        (candidate_dir / "RETURN_TO_CHATGPT.txt").write_text(FORMAL_RTCG, encoding="utf-8")
        (candidate_dir / "merge_signoff.txt").write_text(VALID_MERGE_SIGNOFF, encoding="utf-8")
        (candidate_dir / "push_signoff.txt").write_text(VALID_PUSH_SIGNOFF, encoding="utf-8")
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")
        complete, missing = checker.check_completeness(candidate_dir)
        assert complete, f"Expected complete, got missing: {missing}"
        assert not any("governance_gate" in m for m in missing)
