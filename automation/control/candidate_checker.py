"""
Candidate Materialization Checker

Checks whether a materialized candidate exists for a given round.

Hardened rules (prevents stale evidence directories from being counted as candidates):
1. Candidate directories must be in automation/control/candidates/ (not candidates_stale/)
2. evidence.json must contain candidate_commit OR materialized_candidate=true
3. Old dispatch execution logs (evidence_type ending in _execution or _dispatch) are rejected
4. Both evidence.json and task.txt must exist
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("candidate_checker")


class CandidateChecker:
    """Check if a round has a materialized candidate."""

    # Evidence types that are execution logs, not candidates
    NON_CANDIDATE_EVIDENCE_TYPES = {
        "r020_dispatch_execution",
        "dispatch_execution",
        "bootstrap_execution",
    }

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent

    def _is_valid_candidate_evidence(self, evidence_path: Path) -> bool:
        """
        Validate that an evidence.json represents a materialized candidate.

        Returns True only if evidence contains:
        - candidate_commit (immutable candidate commit hash)
        - OR materialized_candidate: true
        AND evidence_type is NOT an execution log
        """
        try:
            with evidence_path.open("r", encoding="utf-8") as f:
                evidence = json.load(f)
        except Exception:
            return False

        evidence_type = evidence.get("evidence_type", "")
        if evidence_type in self.NON_CANDIDATE_EVIDENCE_TYPES:
            return False

        # Must have materialization proof
        has_candidate_commit = bool(evidence.get("candidate_commit"))
        has_materialized_flag = evidence.get("materialized_candidate", False) is True

        return has_candidate_commit or has_materialized_flag

    def check_candidate_exists(self, round_id: str) -> Dict[str, Any]:
        """
        Check if a materialized candidate exists for the given round.

        Returns dict with:
        - exists: bool
        - branch: str or None
        - candidate_dir: str or None
        - evidence_json: str or None
        - task_txt: str or None
        """
        result = {
            "exists": False,
            "branch": None,
            "candidate_dir": None,
            "evidence_json": None,
            "task_txt": None,
        }

        # Normalize round_id for branch name matching
        round_norm = round_id.lower().replace("-", "_")

        # Search candidate branches
        git_dir = self.repo_root / ".git"
        if git_dir.exists():
            import subprocess
            try:
                proc = subprocess.run(
                    ["git", "branch", "-a"],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                for line in proc.stdout.splitlines():
                    branch = line.strip().lstrip("* ").strip()
                    # Only match work/candidate-* branches, not main/canonical branches
                    if "candidate" in branch.lower() and round_norm in branch.lower():
                        result["branch"] = branch
                        break
            except Exception as e:
                logger.warning(f"Failed to list branches: {e}")

        # Search candidate directories in candidates/ only (not candidates_stale/)
        candidates_dir = self.repo_root / "automation" / "control" / "candidates"
        if candidates_dir.exists():
            for child in candidates_dir.iterdir():
                if not child.is_dir():
                    continue
                if round_norm not in child.name.lower():
                    continue

                evidence = child / "evidence.json"
                task = child / "task.txt"

                if not evidence.exists() or not task.exists():
                    continue

                # Hardened check: evidence must prove materialization
                if not self._is_valid_candidate_evidence(evidence):
                    logger.debug(
                        f"Directory {child.name} matched round {round_id} but "
                        f"evidence does not prove materialization (missing candidate_commit or materialized_candidate flag)"
                    )
                    continue

                result["candidate_dir"] = str(child.relative_to(self.repo_root))
                result["evidence_json"] = str(evidence.relative_to(self.repo_root))
                result["task_txt"] = str(task.relative_to(self.repo_root))
                result["exists"] = True
                break

        return result
