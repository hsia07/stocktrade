import pytest
import json
from pathlib import Path
import tempfile
import shutil

from scripts.validation.validate_canonical_repair_evidence import (
    validate_candidate,
    check_evidence_json,
    check_candidate_diff,
    check_return_to_chatgpt,
    check_test_output_not_substituted,
    check_path_in_authorized_scope,
    check_file_exists,
    check_governance_record_diff_scope,
    classify_candidate,
    REQUIRED_FILES,
)

CANONICAL_HASH = "904f4604b85800194725ad3fe8abd3ee71ec45a9"

FORMAL_RTCG = (
    "round_id: TEST\n"
    "formal_status_code: test\n"
    "base_head: 904f4604b85800194725ad3fe8abd3ee71ec45a9\n"
    "candidate_branch: test\n"
    "candidate_commit: test\n"
    "recommendation: test candidate\n"
    "remaining blockers: none\n"
)

SUMMARY_RTCG = "Just a short summary."


def _create_evidence_dir(tmp: Path, overrides: dict = None):
    """Create a valid evidence package. Returns (tmp, ev_dict)."""
    ev = {
        "round_id": "test", "trace_id": "t1",
        "law_compliance": "04", "evidence_type": "test",
        "round": "1", "phase": "1", "append_only_audit": True,
        "candidate_commit": CANONICAL_HASH,
    }
    if overrides:
        ev.update(overrides)
    (tmp / "evidence.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
    (tmp / "candidate.diff").write_text("dummy diff content here\n", encoding="utf-8")
    (tmp / "RETURN_TO_CHATGPT.txt").write_text(FORMAL_RTCG, encoding="utf-8")
    (tmp / "test-results.txt").write_text("TEST RESULTS\npassed: 1\nfailed: 0\n", encoding="utf-8")
    (tmp / "task.txt").write_text("task_id: TEST\ntask_type: test\nphase: 1\nlaw_compliance: 04\nseverity: medium\n", encoding="utf-8")
    return tmp, ev


class TestValidateCanonicalRepairEvidence:
    """Tests for validate_canonical_repair_evidence.py."""

    @pytest.fixture
    def candidate_dir(self):
        d = Path(tempfile.mkdtemp(prefix="repair_test_"))
        yield d
        shutil.rmtree(d, ignore_errors=True)

    def _in_candidates(self, tmp: Path) -> Path:
        """Place tmp under automation/control/candidates/ to pass scope check."""
        base = Path(tempfile.mkdtemp(prefix="candidates_scope_"))
        target = base / "automation/control/candidates/test_round"
        target.mkdir(parents=True, exist_ok=True)
        # Copy files
        for f in tmp.iterdir():
            shutil.copy2(f, target / f.name)
        return target

    # --- check_file_exists ---

    def test_file_exists_ok(self, candidate_dir):
        (candidate_dir / "foo.txt").write_text("hello", encoding="utf-8")
        ok, msg = check_file_exists(candidate_dir, "foo.txt")
        assert ok
        assert msg == ""

    def test_file_missing(self, candidate_dir):
        ok, msg = check_file_exists(candidate_dir, "nonexistent.txt")
        assert not ok
        assert "missing" in msg

    def test_file_empty(self, candidate_dir):
        (candidate_dir / "empty.txt").write_text("", encoding="utf-8")
        ok, msg = check_file_exists(candidate_dir, "empty.txt")
        assert not ok
        assert "empty" in msg

    # --- check_evidence_json ---

    def test_evidence_json_valid(self, candidate_dir):
        _create_evidence_dir(candidate_dir)
        ok, issues = check_evidence_json(candidate_dir)
        assert ok, f"Expected OK, got {issues}"

    def test_evidence_json_missing(self, candidate_dir):
        ok, issues = check_evidence_json(candidate_dir)
        assert not ok
        assert any("missing" in i for i in issues)

    def test_evidence_json_wrong_law(self, candidate_dir):
        _create_evidence_dir(candidate_dir, {"law_compliance": "99"})
        ok, issues = check_evidence_json(candidate_dir)
        assert not ok
        assert any("law_compliance" in i for i in issues)

    def test_evidence_json_missing_law(self, candidate_dir):
        _create_evidence_dir(candidate_dir, {"law_compliance": None})
        ok, issues = check_evidence_json(candidate_dir)
        assert not ok
        assert any("law_compliance" in i for i in issues)

    def test_evidence_json_forbidden_claim(self, candidate_dir):
        _create_evidence_dir(candidate_dir, {"order_execution_allowed": True})
        ok, issues = check_evidence_json(candidate_dir)
        assert not ok
        assert any("forbidden_claim" in i for i in issues)

    def test_evidence_json_runtime_started(self, candidate_dir):
        _create_evidence_dir(candidate_dir, {"runtime_started": True})
        ok, issues = check_evidence_json(candidate_dir)
        assert not ok
        assert any("forbidden_claim" in i for i in issues)

    # --- check_candidate_diff ---

    def test_candidate_diff_valid(self, candidate_dir):
        _create_evidence_dir(candidate_dir)
        ok, issues = check_candidate_diff(candidate_dir)
        assert ok, f"Expected OK, got {issues}"

    def test_candidate_diff_missing(self, candidate_dir):
        _create_evidence_dir(candidate_dir)
        (candidate_dir / "candidate.diff").unlink()
        ok, issues = check_candidate_diff(candidate_dir)
        assert not ok
        assert any("missing" in i for i in issues)

    def test_candidate_diff_empty(self, candidate_dir):
        _create_evidence_dir(candidate_dir)
        (candidate_dir / "candidate.diff").write_text("", encoding="utf-8")
        ok, issues = check_candidate_diff(candidate_dir)
        assert not ok
        assert any("empty" in i for i in issues)

    def test_candidate_diff_bom(self, candidate_dir):
        _create_evidence_dir(candidate_dir)
        (candidate_dir / "candidate.diff").write_text("\ufeffdummy diff", encoding="utf-8")
        ok, issues = check_candidate_diff(candidate_dir)
        assert not ok
        assert any("utf8_bom" in i for i in issues)

    # --- check_return_to_chatgpt ---

    def test_rtcg_valid(self, candidate_dir):
        _create_evidence_dir(candidate_dir)
        ok, issues = check_return_to_chatgpt(candidate_dir)
        assert ok, f"Expected OK, got {issues}"

    def test_rtcg_missing(self, candidate_dir):
        _create_evidence_dir(candidate_dir)
        (candidate_dir / "RETURN_TO_CHATGPT.txt").unlink()
        ok, issues = check_return_to_chatgpt(candidate_dir)
        assert not ok
        assert any("missing" in i for i in issues)

    def test_rtcg_too_short(self, candidate_dir):
        _create_evidence_dir(candidate_dir)
        (candidate_dir / "RETURN_TO_CHATGPT.txt").write_text(SUMMARY_RTCG, encoding="utf-8")
        ok, issues = check_return_to_chatgpt(candidate_dir)
        assert not ok
        assert any("too_short" in i for i in issues)

    def test_rtcg_missing_marker(self, candidate_dir):
        _create_evidence_dir(candidate_dir)
        (candidate_dir / "RETURN_TO_CHATGPT.txt").write_text(
            "just some text without any formal markers " * 20, encoding="utf-8"
        )
        ok, issues = check_return_to_chatgpt(candidate_dir)
        assert not ok
        assert any("missing_marker" in i for i in issues)

    # --- check_test_output_not_substituted ---

    def test_test_output_allowed_with_test_results(self, candidate_dir):
        (candidate_dir / "test-results.txt").write_text("ok", encoding="utf-8")
        (candidate_dir / "test_output.txt").write_text("also ok", encoding="utf-8")
        ok, issues = check_test_output_not_substituted(candidate_dir)
        assert ok

    def test_test_output_substituted(self, candidate_dir):
        (candidate_dir / "test_output.txt").write_text("only this", encoding="utf-8")
        ok, issues = check_test_output_not_substituted(candidate_dir)
        assert not ok
        assert any("test_output_substituted" in i for i in issues)

    # --- check_path_in_authorized_scope ---

    def test_path_in_scope(self):
        p = Path("automation/control/candidates/test/evidence.json")
        ok, issues = check_path_in_authorized_scope(p.parent)
        assert ok

    def test_path_out_of_scope(self, candidate_dir):
        ok, issues = check_path_in_authorized_scope(candidate_dir)
        assert not ok
        assert any("path_out_of_scope" in i for i in issues)

    # --- validate_candidate (integration) ---

    def test_valid_candidate_passes(self, candidate_dir):
        target = self._in_candidates(candidate_dir)
        _create_evidence_dir(candidate_dir)
        # Re-copy to target
        for f in candidate_dir.iterdir():
            shutil.copy2(f, target / f.name)
        ok, issues, _ = validate_candidate(target)
        assert ok, f"Expected PASS, got {issues}"

    def test_missing_required_files_fails(self, candidate_dir):
        target = self._in_candidates(candidate_dir)
        _create_evidence_dir(candidate_dir)
        for f in candidate_dir.iterdir():
            shutil.copy2(f, target / f.name)
        (target / "RETURN_TO_CHATGPT.txt").unlink()
        ok, issues, _ = validate_candidate(target)
        assert not ok
        assert any("missing:RETURN_TO_CHATGPT.txt" in i for i in issues)


GOV_ACCEPTANCE_DIFF_GOVERNANCE_ONLY = """\
diff --git a/automation/control/governance/r035-governance-record.json b/automation/control/governance/r035-governance-record.json
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/automation/control/governance/r035-governance-record.json
@@ -0,0 +1,80 @@
+{"round_id": "R035", "acceptance_path": "governance_record_acceptance_path"}
diff --git a/automation/control/candidates/R035_GOVERNANCE_RECORD_ACCEPTANCE/evidence.json b/automation/control/candidates/R035_GOVERNANCE_RECORD_ACCEPTANCE/evidence.json
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/automation/control/candidates/R035_GOVERNANCE_RECORD_ACCEPTANCE/evidence.json
@@ -0,0 +1,80 @@
+{"round_id": "R035"}
"""

GOV_ACCEPTANCE_DIFF_WITH_SOURCE = """\
diff --git a/modules/decision_prechecklist/verification_framework.py b/modules/decision_prechecklist/verification_framework.py
index 1234567..89abcde 100644
--- a/modules/decision_prechecklist/verification_framework.py
+++ b/modules/decision_prechecklist/verification_framework.py
@@ -1,5 +1,8 @@
+unauthorized change
diff --git a/automation/control/governance/r035-governance-record.json b/automation/control/governance/r035-governance-record.json
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/automation/control/governance/r035-governance-record.json
@@ -0,0 +1,80 @@
+{"round_id": "R035"}
"""

GOV_ACCEPTANCE_DIFF_WITH_SERVER_V2 = """\
diff --git a/server_v2.py b/server_v2.py
index 1234567..89abcde 100644
--- a/server_v2.py
+++ b/server_v2.py
@@ -1,5 +1,8 @@
+unauthorized change
diff --git a/automation/control/governance/r035-governance-record.json b/automation/control/governance/r035-governance-record.json
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/automation/control/governance/r035-governance-record.json
@@ -0,0 +1,80 @@
+{"round_id": "R035"}
"""

GOV_ACCEPTANCE_DIFF_WITH_TESTS = """\
diff --git a/tests/test_verification_framework.py b/tests/test_verification_framework.py
index 1234567..89abcde 100644
--- a/tests/test_verification_framework.py
+++ b/tests/test_verification_framework.py
@@ -1,5 +1,8 @@
+unauthorized change
diff --git a/automation/control/governance/r035-governance-record.json b/automation/control/governance/r035-governance-record.json
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/automation/control/governance/r035-governance-record.json
@@ -0,0 +1,80 @@
+{"round_id": "R035"}
"""

GOV_ACCEPTANCE_EVIDENCE = {
    "round_id": "R035",
    "task_type": "governance_record_acceptance_candidate",
    "acceptance_path": "governance_record_acceptance_path",
    "formal_status_code": "R035_GOVERNANCE_RECORD_ACCEPTANCE_CANDIDATE_READY",
    "law_compliance": "04",
    "broker_api_called": False,
    "trading_runtime_started": False,
    "order_execution_allowed": False,
    "r049_started": False,
    "r036_R048_accepted": False,
}

# --- check_governance_record_diff_scope ---

class TestGovernanceRecordDiffScope:

    def test_governance_only_diff_passes(self, tmp_path):
        (tmp_path / "candidate.diff").write_text(GOV_ACCEPTANCE_DIFF_GOVERNANCE_ONLY, encoding="utf-8")
        ok, issues = check_governance_record_diff_scope(tmp_path)
        assert ok, f"Expected PASS, got {issues}"

    def test_source_diff_fails(self, tmp_path):
        (tmp_path / "candidate.diff").write_text(GOV_ACCEPTANCE_DIFF_WITH_SOURCE, encoding="utf-8")
        ok, issues = check_governance_record_diff_scope(tmp_path)
        assert not ok, "Expected FAIL for governance record with source changes"
        assert any("forbidden_path" in i for i in issues)

    def test_server_v2_diff_fails(self, tmp_path):
        (tmp_path / "candidate.diff").write_text(GOV_ACCEPTANCE_DIFF_WITH_SERVER_V2, encoding="utf-8")
        ok, issues = check_governance_record_diff_scope(tmp_path)
        assert not ok, "Expected FAIL for governance record with server_v2 changes"
        assert any("forbidden_path" in i for i in issues)

    def test_missing_diff_skipped(self, tmp_path):
        ok, issues = check_governance_record_diff_scope(tmp_path)
        assert ok, "Expected PASS when no diff file exists"


# --- classify_candidate ---

class TestClassifyCandidateGovernanceRecord:

    def test_governance_record_acceptance_classified(self, tmp_path):
        ev = dict(GOV_ACCEPTANCE_EVIDENCE)
        (tmp_path / "evidence.json").write_text(json.dumps(ev), encoding="utf-8")
        cls = classify_candidate(tmp_path)
        assert cls == "governance_record_acceptance", f"Expected governance_record_acceptance, got {cls}"

    def test_regular_candidate_not_misclassified(self, tmp_path):
        ev = {
            "round_id": "test", "trace_id": "t1",
            "law_compliance": "04", "evidence_type": "test",
        }
        (tmp_path / "evidence.json").write_text(json.dumps(ev), encoding="utf-8")
        cls = classify_candidate(tmp_path)
        assert cls != "governance_record_acceptance", "Regular candidate should not be governance_record_acceptance"
        assert cls == "valid_acceptance_candidate"


# --- validate_candidate with governance record ---

class TestValidateGovernanceRecordCandidate:

    def _setup_governance_candidate(self, tmp: Path, diff_content: str, ev_overrides: dict = None) -> Path:
        ev = dict(GOV_ACCEPTANCE_EVIDENCE)
        if ev_overrides:
            ev.update(ev_overrides)
        (tmp / "evidence.json").write_text(json.dumps(ev, indent=2), encoding="utf-8")
        (tmp / "candidate.diff").write_text(diff_content, encoding="utf-8")
        (tmp / "RETURN_TO_CHATGPT.txt").write_text(FORMAL_RTCG, encoding="utf-8")
        (tmp / "test-results.txt").write_text("TEST RESULTS\npassed: 1\nfailed: 0\n", encoding="utf-8")
        (tmp / "task.txt").write_text("task_id: R035\ntask_type: governance_record_acceptance\nlaw_compliance: 04\n", encoding="utf-8")
        base = Path(tempfile.mkdtemp(prefix="candidates_scope_"))
        target = base / "automation/control/candidates/R035_GOVERNANCE_RECORD_ACCEPTANCE"
        target.mkdir(parents=True, exist_ok=True)
        for f in tmp.iterdir():
            shutil.copy2(f, target / f.name)
        return target

    def test_governance_record_acceptance_passes(self, tmp_path):
        target = self._setup_governance_candidate(tmp_path, GOV_ACCEPTANCE_DIFF_GOVERNANCE_ONLY)
        ok, issues, cls = validate_candidate(target)
        assert ok, f"Expected PASS, got {issues}"
        assert cls == "governance_record_acceptance"

    def test_governance_record_with_source_fails(self, tmp_path):
        target = self._setup_governance_candidate(tmp_path, GOV_ACCEPTANCE_DIFF_WITH_SOURCE)
        ok, issues, cls = validate_candidate(target)
        assert not ok, "Expected FAIL for governance record with source changes"
        assert cls == "governance_record_acceptance"
        assert any("forbidden_path" in i for i in issues)

    def test_governance_record_with_server_v2_fails(self, tmp_path):
        target = self._setup_governance_candidate(tmp_path, GOV_ACCEPTANCE_DIFF_WITH_SERVER_V2)
        ok, issues, cls = validate_candidate(target)
        assert not ok, "Expected FAIL for governance record with server_v2 changes"
        assert cls == "governance_record_acceptance"
        assert any("forbidden_path" in i for i in issues)

    def test_governance_record_missing_evidence_json_fails(self, tmp_path):
        target = self._setup_governance_candidate(tmp_path, GOV_ACCEPTANCE_DIFF_GOVERNANCE_ONLY)
        (target / "evidence.json").unlink()
        ok, issues, cls = validate_candidate(target)
        assert not ok
        assert any("missing:evidence.json" in i for i in issues)
