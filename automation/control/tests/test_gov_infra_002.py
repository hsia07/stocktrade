"""
GOV-INFRA-002 runtime tests: evidence package freshness check.

Verifies:
- Fresh candidate evidence (< 7 days) → PASS
- Stale candidate evidence (> 7 days) → FAIL / blocked
- Historical canonical reconciled round → EXEMPT / PASS
- Missing evidence package / missing git timestamp → FAIL
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from automation.control.evidence_checker import EvidenceChecker

FRESHNESS_ROUND = "gov_infra_002_freshness"
STALE_ROUND = "STALE-ROUND"
HISTORICAL_ROUND = "HISTORICAL-ROUND-001"
STALE_INTEGRATION = "STALE-INTEGRATION"

EIGHT_DAYS_AGO = int(time.time()) - 8 * 24 * 60 * 60


def _make_candidate_dir(
    repo_dir: Path,
    round_id: str,
    status: str = "completed",
    candidate_commit: str | None = None,
) -> Path:
    """Create a candidate dir with report.json, evidence.json, task.txt."""
    cand_dir = repo_dir / "candidates" / round_id
    cand_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "round_id": round_id,
        "status": status,
        "candidate_branch": f"work/candidate-{round_id.lower()}-001",
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

    (cand_dir / "task.txt").write_text(f"=== {round_id} ===\n", encoding="utf-8")

    return cand_dir


def _git_commit_all(
    repo_dir: Path,
    message: str,
    unix_timestamp: int | None = None,
) -> str:
    """Stage all, commit with optional old unix_timestamp, return hash."""
    env = os.environ.copy()
    ts_str = str(unix_timestamp) if unix_timestamp else None
    if ts_str:
        env["GIT_COMMITTER_DATE"] = ts_str
    subprocess.run(["git", "add", "-A"], capture_output=True, cwd=repo_dir, env=env)
    args = ["git", "commit", "-m", message]
    if ts_str:
        args.extend(["--date", ts_str])
    r = subprocess.run(args, capture_output=True, text=True, cwd=repo_dir, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"commit failed: {r.stderr}")
    # Reliably get the hash via rev-parse
    r2 = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True, text=True, cwd=repo_dir, env=env,
    )
    return r2.stdout.strip()


def _init_repo(repo_dir: Path) -> None:
    """Initialize a git repo with one initial commit."""
    repo_dir.mkdir()
    subprocess.run(["git", "init"], capture_output=True, cwd=repo_dir)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        capture_output=True, cwd=repo_dir,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        capture_output=True, cwd=repo_dir,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "initial"],
        capture_output=True, cwd=repo_dir,
    )


def _setup_bare_remote(repo_dir: Path) -> Path:
    """Create a bare remote repo and push all branches to it."""
    bare_dir = repo_dir.parent / "remote.git"
    subprocess.run(["git", "init", "--bare", str(bare_dir)], capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", str(bare_dir)],
        capture_output=True, cwd=repo_dir,
    )
    subprocess.run(
        ["git", "push", "--all", "origin"],
        capture_output=True, cwd=repo_dir,
    )
    return bare_dir


class TestFreshCandidatePasses:
    """Candidate evidence with latest commit < 7 days must pass."""

    def test_fresh_candidate_passes(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "git_repo"
        _init_repo(repo_dir)
        cand_dir = _make_candidate_dir(repo_dir, FRESHNESS_ROUND)
        _git_commit_all(repo_dir, "add fresh candidate evidence")

        checker = EvidenceChecker(repo_dir)
        is_fresh, reason = checker.check_evidence_freshness(cand_dir)
        assert is_fresh is True, f"fresh candidate should pass, got reason={reason}"
        assert "evidence_fresh" in reason, f"reason must indicate fresh, got: {reason}"


class TestStaleCandidateBlocked:
    """Candidate evidence with latest commit > 7 days must fail."""

    def test_8day_old_candidate_blocked(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "git_repo"
        _init_repo(repo_dir)
        cand_dir = _make_candidate_dir(repo_dir, STALE_ROUND)
        _git_commit_all(repo_dir, "add stale candidate evidence", EIGHT_DAYS_AGO)

        checker = EvidenceChecker(repo_dir)
        is_fresh, reason = checker.check_evidence_freshness(cand_dir)
        assert is_fresh is False, (
            f"8-day old candidate should be stale, got reason={reason}"
        )
        assert "evidence_stale" in reason, f"reason must indicate stale, got: {reason}"


class TestHistoricalCanonicalRoundExempt:
    """Historical canonical reconciled rounds must be EXEMPT from freshness check."""

    def test_historical_round_exempt(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "git_repo"
        _init_repo(repo_dir)

        feature_branch = "work/candidate-historical-001"
        canonical_branch = "work/canonical-mainline-repair-001"

        # Create feature branch for candidate work
        subprocess.run(
            ["git", "checkout", "-b", feature_branch],
            capture_output=True, cwd=repo_dir,
        )

        # Create candidate evidence files (all with old timestamp)
        cand_dir = _make_candidate_dir(
            repo_dir, HISTORICAL_ROUND, status="ready_for_merge_signoff",
        )
        cand_hash = _git_commit_all(
            repo_dir, "add historical evidence files", EIGHT_DAYS_AGO,
        )

        # Add candidate_commit to evidence.json (still with old timestamp)
        evidence_path = cand_dir / "evidence.json"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["candidate_commit"] = cand_hash
        evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

        _git_commit_all(repo_dir, "update evidence with commit hash", EIGHT_DAYS_AGO)

        # Create canonical branch from master, checkout canonical, merge feature
        subprocess.run(
            ["git", "branch", canonical_branch, "master"],
            capture_output=True, cwd=repo_dir,
        )
        subprocess.run(
            ["git", "checkout", canonical_branch],
            capture_output=True, cwd=repo_dir,
        )
        merge_result = subprocess.run(
            ["git", "merge", "--no-ff", feature_branch, "-m", "merge historical round"],
            capture_output=True, text=True, cwd=repo_dir,
        )
        if merge_result.returncode != 0:
            print(f"merge stderr: {merge_result.stderr[:500]}")

        # Setup remote and push canonical branch (reconciliation)
        _setup_bare_remote(repo_dir)

        checker = EvidenceChecker(repo_dir)
        is_fresh, reason = checker.check_evidence_freshness(cand_dir)
        assert is_fresh is True, (
            f"historical canonical round should be exempt, got reason={reason}"
        )
        assert "historical_canonical_round" in reason, (
            f"reason must mention historical exemption, got: {reason}"
        )


class TestMissingTimestampFails:
    """Missing evidence package or missing git timestamp must fail cleanly."""

    def test_nonexistent_dir_fails(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        fake_dir = tmp_path / "candidates" / "NONEXISTENT"
        success, timestamp = checker.get_evidence_latest_commit_timestamp(fake_dir)
        assert success is False, "nonexistent dir must return failure"

    def test_untracked_evidence_fails(self, tmp_path: Path) -> None:
        """Evidence files in git repo but never committed must fail."""
        repo_dir = tmp_path / "git_repo"
        _init_repo(repo_dir)

        untracked_dir = repo_dir / "candidates" / "UNTRACKED"
        untracked_dir.mkdir(parents=True)
        (untracked_dir / "evidence.json").write_text("{}", encoding="utf-8")

        checker = EvidenceChecker(repo_dir)
        is_fresh, reason = checker.check_evidence_freshness(untracked_dir)
        assert is_fresh is False, "untracked evidence must not be fresh"
        assert "evidence_timestamp_unavailable:error_code=-3" in reason, (
            f"reason must indicate missing git timestamp (-3), got: {reason}"
        )

    def test_check_completeness_integrates_freshness(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "git_repo"
        _init_repo(repo_dir)
        cand_dir = _make_candidate_dir(repo_dir, STALE_INTEGRATION, status="completed")
        _git_commit_all(repo_dir, "add stale evidence", EIGHT_DAYS_AGO)

        checker = EvidenceChecker(repo_dir)
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is False, "stale evidence must be incomplete via check_completeness"
        assert any("evidence_stale" in m for m in missing), (
            f"missing must include evidence_stale, got: {missing}"
        )


if __name__ == "__main__":
    passed = 0
    failed = 0
    fail_list = []
    tests = [
        ("test_fresh_candidate_passes",
         TestFreshCandidatePasses().test_fresh_candidate_passes),
        ("test_8day_old_candidate_blocked",
         TestStaleCandidateBlocked().test_8day_old_candidate_blocked),
        ("test_historical_round_exempt",
         TestHistoricalCanonicalRoundExempt().test_historical_round_exempt),
        ("test_nonexistent_dir_fails",
         TestMissingTimestampFails().test_nonexistent_dir_fails),
        ("test_empty_dir_untracked_fails",
         TestMissingTimestampFails().test_empty_dir_untracked_fails),
        ("test_check_completeness_integrates_freshness",
         TestMissingTimestampFails().test_check_completeness_integrates_freshness),
    ]
    for name, fn in tests:
        try:
            fn()
            print(f"PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {name}: {e}")
            failed += 1
            fail_list.append(name)
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        print(f"Failures: {fail_list}")
        exit(1)
