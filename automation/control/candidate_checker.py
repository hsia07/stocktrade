"""
Candidate Materialization Checker

Checks whether a candidate branch and evidence package exist for a given round.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("candidate_checker")


class CandidateChecker:
    """Check if a round has a materialized candidate."""

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent

    def check_candidate_exists(self, round_id: str) -> Dict[str, Any]:
        """
        Check if a candidate exists for the given round.

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
                    if round_norm in branch.lower():
                        result["branch"] = branch
                        break
            except Exception as e:
                logger.warning(f"Failed to list branches: {e}")

        # Search candidate directories
        candidates_dir = self.repo_root / "automation" / "control" / "candidates"
        if candidates_dir.exists():
            for child in candidates_dir.iterdir():
                if child.is_dir() and round_norm in child.name.lower():
                    result["candidate_dir"] = str(child.relative_to(self.repo_root))
                    evidence = child / "evidence.json"
                    task = child / "task.txt"
                    if evidence.exists():
                        result["evidence_json"] = str(evidence.relative_to(self.repo_root))
                    if task.exists():
                        result["task_txt"] = str(task.relative_to(self.repo_root))
                    if result["evidence_json"] and result["task_txt"]:
                        result["exists"] = True
                    break

        return result
