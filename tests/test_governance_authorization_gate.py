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

    # --- No signoff files ---

    def test_no_files_returns_issue(self, checker, candidate_dir):
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:no_authorization_files_found" in i for i in issues)

    # --- Valid signoffs ---

    def test_merge_signoff_valid_passes(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(VALID_MERGE_SIGNOFF, encoding="utf-8")
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert not any(i.startswith("governance_gate:") for i in issues)

    def test_push_signoff_valid_passes(self, checker, candidate_dir):
        (candidate_dir / "push_signoff.txt").write_text(VALID_PUSH_SIGNOFF, encoding="utf-8")
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert not any(i.startswith("governance_gate:") for i in issues)

    def test_both_signoffs_valid_passes(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(VALID_MERGE_SIGNOFF, encoding="utf-8")
        (candidate_dir / "push_signoff.txt").write_text(VALID_PUSH_SIGNOFF, encoding="utf-8")
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert not any(i.startswith("governance_gate:") for i in issues)

    # --- Too short ---

    def test_merge_signoff_too_short(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text("ok", encoding="utf-8")
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:merge_signoff_too_short" in i for i in issues)

    def test_push_signoff_too_short(self, checker, candidate_dir):
        (candidate_dir / "push_signoff.txt").write_text("no", encoding="utf-8")
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:push_signoff_too_short" in i for i in issues)

    # --- Missing authorization text ---

    def test_merge_signoff_missing_auth_text(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(
            "merge for work/canonical-mainline-repair-001 "
            "at 904f4604b85800194725ad3fe8abd3ee71ec45a9 no auth"
        )
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:merge_signoff_missing_authorization_text" in i for i in issues)

    def test_push_signoff_missing_auth_text(self, checker, candidate_dir):
        (candidate_dir / "push_signoff.txt").write_text(
            "push for work/canonical-mainline-repair-001 "
            "at 904f4604b85800194725ad3fe8abd3ee71ec45a9 no auth"
        )
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:push_signoff_missing_authorization_text" in i for i in issues)

    # --- Empty file ---

    def test_empty_file_treated_as_missing(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text("", encoding="utf-8")
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:no_authorization_files_found" in i for i in issues)

    # --- Missing action type ---

    def test_merge_signoff_missing_action_type(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(
            "Authorized for work/canonical-mainline-repair-001 "
            "at 904f4604b85800194725ad3fe8abd3ee71ec45a9 consent"
        )
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:merge_signoff_missing_action_type" in i for i in issues)

    def test_push_signoff_missing_action_type(self, checker, candidate_dir):
        (candidate_dir / "push_signoff.txt").write_text(
            "Authorized for work/canonical-mainline-repair-001 "
            "at 904f4604b85800194725ad3fe8abd3ee71ec45a9 consent"
        )
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:push_signoff_missing_action_type" in i for i in issues)

    # --- Missing target branch ---

    def test_merge_signoff_missing_branch(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(
            "Merge authorized at 904f4604b85800194725ad3fe8abd3ee71ec45a9 consent"
        )
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:merge_signoff_missing_target_branch" in i for i in issues)

    def test_push_signoff_missing_branch(self, checker, candidate_dir):
        (candidate_dir / "push_signoff.txt").write_text(
            "Push authorized at 904f4604b85800194725ad3fe8abd3ee71ec45a9 consent"
        )
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:push_signoff_missing_target_branch" in i for i in issues)

    # --- Missing hash ---

    def test_merge_signoff_missing_hash(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(
            "Merge authorized for work/canonical-mainline-repair-001 by consent"
        )
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:merge_signoff_missing_hash" in i for i in issues)

    def test_push_signoff_missing_hash(self, checker, candidate_dir):
        (candidate_dir / "push_signoff.txt").write_text(
            "Push authorized for work/canonical-mainline-repair-001 by consent"
        )
        self._write_evidence(candidate_dir, {"round_id": "test"})
        issues = checker._check_governance_authorization_gate({}, candidate_dir)
        assert any("governance_gate:push_signoff_missing_hash" in i for i in issues)

    # --- check_completeness integration ---

    def test_check_completeness_includes_gate(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(VALID_MERGE_SIGNOFF, encoding="utf-8")
        (candidate_dir / "push_signoff.txt").write_text(VALID_PUSH_SIGNOFF, encoding="utf-8")
        (candidate_dir / "task.txt").write_text("task_id: TEST\ntask_type: test\nphase: 1\nlaw_compliance: 04\nseverity: medium", encoding="utf-8")
        (candidate_dir / "report.json").write_text(json.dumps({
            "round_id": "test", "status": "completed",
            "canonical_branch": "origin/work/canonical-mainline-repair-001",
            "canonical_head": CANONICAL_HASH,
            "test_count": 1, "tests_passed": 1
        }, indent=2), encoding="utf-8")
        (candidate_dir / "evidence.json").write_text(json.dumps({
            "round_id": "test", "trace_id": "trace-001",
            "law_compliance": "04", "evidence_type": "test",
            "round": "1", "phase": "1", "append_only_audit": True,
            "candidate_commit": CANONICAL_HASH
        }, indent=2), encoding="utf-8")
        (candidate_dir / "candidate.diff").write_text("dummy diff", encoding="utf-8")
        (candidate_dir / "no-aider-used.txt").write_text("No aider used", encoding="utf-8")
        (candidate_dir / "test-results.txt").write_text("TEST RESULTS\npassed: 1\nfailed: 0", encoding="utf-8")

        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")
        complete, missing = checker.check_completeness(candidate_dir)
        assert complete, f"Expected complete but missing: {missing}"
        assert not any("governance_gate" in m for m in missing)

    def test_check_completeness_fails_without_signoff(self, checker, candidate_dir):
        (candidate_dir / "task.txt").write_text("task_id: TEST\ntask_type: test\nphase: 1\nlaw_compliance: 04\nseverity: medium", encoding="utf-8")
        (candidate_dir / "report.json").write_text(json.dumps({
            "round_id": "test", "status": "completed",
            "canonical_branch": "origin/work/canonical-mainline-repair-001",
            "canonical_head": CANONICAL_HASH,
            "test_count": 1, "tests_passed": 1
        }, indent=2), encoding="utf-8")
        (candidate_dir / "evidence.json").write_text(json.dumps({
            "round_id": "test", "trace_id": "trace-001",
            "law_compliance": "04", "evidence_type": "test",
            "round": "1", "phase": "1", "append_only_audit": True,
            "candidate_commit": CANONICAL_HASH
        }, indent=2), encoding="utf-8")
        (candidate_dir / "candidate.diff").write_text("dummy diff", encoding="utf-8")
        (candidate_dir / "no-aider-used.txt").write_text("No aider used", encoding="utf-8")
        (candidate_dir / "test-results.txt").write_text("TEST RESULTS\npassed: 1\nfailed: 0", encoding="utf-8")
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")

        complete, missing = checker.check_completeness(candidate_dir)
        assert not complete
        assert any("governance_gate:no_authorization_files_found" in m for m in missing)

    # --- Incomplete evidence package (missing candidate.diff) ---

    def test_incomplete_evidence_missing_candidate_diff(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(VALID_MERGE_SIGNOFF, encoding="utf-8")
        (candidate_dir / "push_signoff.txt").write_text(VALID_PUSH_SIGNOFF, encoding="utf-8")
        (candidate_dir / "task.txt").write_text("task_id: TEST\ntask_type: test\nphase: 1\nlaw_compliance: 04\nseverity: medium", encoding="utf-8")
        (candidate_dir / "report.json").write_text(json.dumps({
            "round_id": "test", "status": "completed",
            "canonical_branch": "origin/work/canonical-mainline-repair-001",
            "canonical_head": CANONICAL_HASH,
            "test_count": 1, "tests_passed": 1
        }, indent=2), encoding="utf-8")
        (candidate_dir / "evidence.json").write_text(json.dumps({
            "round_id": "test", "trace_id": "trace-001",
            "law_compliance": "04", "evidence_type": "test",
            "round": "1", "phase": "1", "append_only_audit": True,
            "candidate_commit": CANONICAL_HASH
        }, indent=2), encoding="utf-8")
        (candidate_dir / "no-aider-used.txt").write_text("No aider used", encoding="utf-8")
        (candidate_dir / "test-results.txt").write_text("TEST RESULTS\npassed: 1\nfailed: 0", encoding="utf-8")
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")

        complete, missing = checker.check_completeness(candidate_dir)
        assert not complete
        assert any("missing:candidate.diff" in m for m in missing)

    # --- Incomplete evidence package (missing test-results.txt) ---

    def test_incomplete_evidence_missing_test_results(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(VALID_MERGE_SIGNOFF, encoding="utf-8")
        (candidate_dir / "push_signoff.txt").write_text(VALID_PUSH_SIGNOFF, encoding="utf-8")
        (candidate_dir / "task.txt").write_text("task_id: TEST\ntask_type: test\nphase: 1\nlaw_compliance: 04\nseverity: medium", encoding="utf-8")
        (candidate_dir / "report.json").write_text(json.dumps({
            "round_id": "test", "status": "completed",
            "canonical_branch": "origin/work/canonical-mainline-repair-001",
            "canonical_head": CANONICAL_HASH,
            "test_count": 1, "tests_passed": 1
        }, indent=2), encoding="utf-8")
        (candidate_dir / "evidence.json").write_text(json.dumps({
            "round_id": "test", "trace_id": "trace-001",
            "law_compliance": "04", "evidence_type": "test",
            "round": "1", "phase": "1", "append_only_audit": True,
            "candidate_commit": CANONICAL_HASH
        }, indent=2), encoding="utf-8")
        (candidate_dir / "candidate.diff").write_text("dummy diff", encoding="utf-8")
        (candidate_dir / "no-aider-used.txt").write_text("No aider used", encoding="utf-8")
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")

        complete, missing = checker.check_completeness(candidate_dir)
        assert not complete
        assert any("missing:test-results.txt" in m for m in missing)

    # --- Incomplete evidence package (missing evidence.json) ---

    def test_incomplete_evidence_missing_evidence_json(self, checker, candidate_dir):
        (candidate_dir / "merge_signoff.txt").write_text(VALID_MERGE_SIGNOFF, encoding="utf-8")
        (candidate_dir / "push_signoff.txt").write_text(VALID_PUSH_SIGNOFF, encoding="utf-8")
        (candidate_dir / "task.txt").write_text("task_id: TEST\ntask_type: test\nphase: 1\nlaw_compliance: 04\nseverity: medium", encoding="utf-8")
        (candidate_dir / "report.json").write_text(json.dumps({
            "round_id": "test", "status": "completed",
            "canonical_branch": "origin/work/canonical-mainline-repair-001",
            "canonical_head": CANONICAL_HASH,
            "test_count": 1, "tests_passed": 1
        }, indent=2), encoding="utf-8")
        (candidate_dir / "candidate.diff").write_text("dummy diff", encoding="utf-8")
        (candidate_dir / "no-aider-used.txt").write_text("No aider used", encoding="utf-8")
        (candidate_dir / "test-results.txt").write_text("TEST RESULTS\npassed: 1\nfailed: 0", encoding="utf-8")
        checker.repo_root = Path(r"C:\Users\richa\OneDrive\桌面\stocktrade")

        complete, missing = checker.check_completeness(candidate_dir)
        assert not complete
        assert any("missing:evidence.json" in m for m in missing)
