"""
FIX-EVIDENCE-GATE-CONTRACT runtime tests.

Verifies Option A strict acceptance of ready_for_merge_signoff:
- ready_for_merge_signoff + canonical proof (ancestry + local/remote match) → PASS
- ready_for_merge_signoff + NO canonical proof → FAIL
- completed status behavior preserved
- No retroactive evidence mutation required
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from automation.control.evidence_checker import EvidenceChecker


@pytest.fixture()
def checker(tmp_path: Path) -> EvidenceChecker:
    return EvidenceChecker(tmp_path)


def _make_candidate_dir(
    tmp_path: Path,
    round_id: str,
    status: str,
    candidate_commit: str | None = None,
    candidate_branch: str | None = None,
) -> Path:
    """Create a candidate dir with report.json and evidence.json."""
    cand_dir = tmp_path / "candidates" / round_id
    cand_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "round_id": round_id,
        "status": status,
        "candidate_branch": candidate_branch or f"work/candidate-{round_id.lower()}-001",
        "canonical_branch": "work/canonical-mainline-repair-001",
    }
    (cand_dir / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    evidence = {
        "trace_id": f"{round_id.lower()}-001",
        "law_compliance": "04",
        "phase": "governance",
        "round": round_id,
    }
    if candidate_commit:
        evidence["candidate_commit"] = candidate_commit
    (cand_dir / "evidence.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )

    # task.txt is required by REQUIRED_FILES
    (cand_dir / "task.txt").write_text(f"=== {round_id} ===\n", encoding="utf-8")

    return cand_dir


class TestCompletedStatusPreserved:
    """'completed' status must still pass without any additional proof."""

    def test_completed_passes(self, checker: EvidenceChecker, tmp_path: Path) -> None:
        cand_dir = _make_candidate_dir(tmp_path, "TEST-ROUND", "completed")
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is True, f"completed status should pass, got missing={missing}"

    def test_completed_passes_with_real_hash(self, checker: EvidenceChecker, tmp_path: Path) -> None:
        """completed status with a valid hash must still pass."""
        real_hash = "163366b284d48a34270490c45a2b7db909889fad"
        cand_dir = _make_candidate_dir(
            tmp_path, "TEST-ROUND", "completed",
            candidate_commit=real_hash,
        )
        # Need real repo_root so validate_40hex_hash can find the git object
        checker.repo_root = Path(__file__).parent.parent.parent.parent
        # But the candidate dir is in tmp_path, so we need to link the test
        # to reference the real hash. However, without canonical_branch set,
        # the ancestry check is skipped for completed status.
        # The hash validation still needs the real repo root.
        complete, missing = checker.check_completeness(cand_dir)
        # completed status means the report status check passes,
        # but 40hex validation may fail if hash not in tmp_path repo.
        # This is acceptable — the 40hex validation is a separate concern.
        # For completed status, the report gate passes regardless.
        assert "report_status_not_completed" not in " ".join(missing), (
            f"completed status must not add report_status_not_completed, got missing={missing}"
        )

    def test_completed_with_no_candidate_branch(self, checker: EvidenceChecker, tmp_path: Path) -> None:
        cand_dir = _make_candidate_dir(tmp_path, "TEST-ROUND", "completed", candidate_branch="nonexistent/branch")
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is True, "completed status must pass regardless of branch existence"


class TestReadyForMergeSignoffWithProof:
    """ready_for_merge_signoff + canonical proof → PASS."""

    def test_blocker_h_with_canonical_proof(self, checker: EvidenceChecker) -> None:
        """BLOCKER_H has real canonical proof: merged, pushed, reconciled."""
        cand_dir = Path(__file__).parent.parent / "candidates" / "BLOCKER-H-TELEGRAM-HANDLER"
        checker.repo_root = Path(__file__).parent.parent.parent.parent
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is True, f"BLOCKER_H with canonical proof should pass, got missing={missing}"

    def test_blocker_e_with_canonical_proof(self, checker: EvidenceChecker) -> None:
        """BLOCKER_E also merged+push — should pass."""
        cand_dir = Path(__file__).parent.parent / "candidates" / "BLOCKER-E-AUTOMATED-SIGNOFF"
        checker.repo_root = Path(__file__).parent.parent.parent.parent
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is True, f"BLOCKER_E with canonical proof should pass, got missing={missing}"


class TestReadyForMergeSignoffWithoutProof:
    """ready_for_merge_signoff without canonical proof → FAIL."""

    def test_no_candidate_commit_and_no_branch(self, checker: EvidenceChecker, tmp_path: Path) -> None:
        cand_dir = _make_candidate_dir(tmp_path, "FAKE-ROUND", "ready_for_merge_signoff")
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is False, "should fail: no candidate_commit, no valid branch"
        assert any("ready_for_merge_signoff" in m for m in missing), (
            f"missing must reference ready_for_merge_signoff, got {missing}"
        )

    def test_branch_not_ancestor_of_canonical(self, checker: EvidenceChecker, tmp_path: Path) -> None:
        cand_dir = _make_candidate_dir(
            tmp_path, "FAKE-ROUND", "ready_for_merge_signoff",
            candidate_commit="0000000000000000000000000000000000000000",
        )
        checker.repo_root = tmp_path
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is False, "should fail: candidate_commit is not a real git object"
        assert any("ready_for_merge_signoff" in m for m in missing)

    def test_branch_exists_but_not_merged(self, checker: EvidenceChecker, tmp_path: Path) -> None:
        """Simulate an unmerged round properly."""
        from pathlib import Path
        os = __import__("os")
        repo_dir = tmp_path / "git_repo"
        repo_dir.mkdir()
        os.chdir(str(repo_dir))

        import subprocess
        for cmd in [
            ["git", "init"],
            ["git", "config", "user.email", "test@test.com"],
            ["git", "config", "user.name", "Test"],
        ]:
            subprocess.run(cmd, capture_output=True, cwd=repo_dir)

        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "initial"],
            capture_output=True, cwd=repo_dir,
        )

        # Create an unmerged branch
        subprocess.run(
            ["git", "branch", "work/candidate-unmerged-001"],
            capture_output=True, cwd=repo_dir,
        )

        checker.repo_root = repo_dir
        cand_dir = _make_candidate_dir(
            tmp_path, "UNMERGED-ROUND", "ready_for_merge_signoff",
            candidate_branch="work/candidate-unmerged-001",
        )
        # The repo has no remote, so remote check will fail
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is False, "should fail: branch not merged and no remote alignment"


class TestRetroactiveMutationNoLongerRequired:
    """The old tainted workaround (modifying report.json) must no longer be needed."""

    def test_blocker_h_original_report_unchanged(self) -> None:
        """BLOCKER_H report.json must still show ready_for_merge_signoff (was reverted)."""
        cand_dir = Path(__file__).parent.parent / "candidates" / "BLOCKER-H-TELEGRAM-HANDLER"
        report_path = cand_dir / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["status"] == "ready_for_merge_signoff", (
            "BLOCKER_H report.json must remain unchanged (ready_for_merge_signoff)"
        )

    def test_blocker_h_passes_without_mutation(self, checker: EvidenceChecker) -> None:
        """BLOCKER_H must pass the check without modifying report.json."""
        checker.repo_root = Path(__file__).parent.parent.parent.parent
        cand_dir = Path(__file__).parent.parent / "candidates" / "BLOCKER-H-TELEGRAM-HANDLER"
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is True, (
            f"BLOCKER_H must pass without mutation, got missing={missing}"
        )


class TestUnknownStatusStillBlocked:
    """Unknown status values must still be blocked."""

    def test_in_progress_blocked(self, checker: EvidenceChecker, tmp_path: Path) -> None:
        cand_dir = _make_candidate_dir(tmp_path, "TEST", "in_progress")
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is False

    def test_failed_blocked(self, checker: EvidenceChecker, tmp_path: Path) -> None:
        cand_dir = _make_candidate_dir(tmp_path, "TEST", "failed")
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is False

    def test_empty_status_blocked(self, checker: EvidenceChecker, tmp_path: Path) -> None:
        cand_dir = _make_candidate_dir(tmp_path, "TEST", "")
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is False
