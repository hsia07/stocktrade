"""
Worktree-Native Auto-Mode Manager (BLOCKER_B remediation)

Resolves auto mode BLOCKER_B: main working tree pollution / isolated worktree dependency.

STRATEGY SELECTED: Plan B (worktree-native auto-mode)
- Candidate build, merge, and push all operate in isolated git worktrees
- Main working tree is NEVER used for round-scoped operations
- Standardized naming: C:/stocktrade-<ROUND>-<PURPOSE>
- Lifecycle tracking via JSON registry at automation/control/worktree_registry.json
- Cleanup rule: worktree kept until round formally closed and push confirmed
- Canonical baseline hard-compare before any operation

Usage:
    from automation.control.worktree_manager import WorktreeManager
    mgr = WorktreeManager()
    mgr.create_worktree("R030", "work/candidate-r030-latency-001", "candidate")
    mgr.assert_clean_baseline("R030", "candidate")
    mgr.remove_worktree("R030", "candidate")
    active = mgr.list_active_worktrees()
"""

import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("worktree_manager")

WORKTREE_REGISTRY = "worktree_registry.json"
WORKTREE_BASE = Path("C:/")

VALID_PURPOSES = {"candidate", "push", "evidence"}


class WorktreeManager:
    """Manage isolated git worktrees for round-scoped operations.

    Architecture:
        Main Repo: C:/Users/richa/.../stocktrade  (canonical, never used for round code)
        Worktrees: C:/stocktrade-<ROUND>-<PURPOSE> (isolated, one per round per purpose)

    Lifecycle:
        create_worktree() → [round operations] → remove_worktree()
        Registry tracks: round_id, purpose, path, branch, canonical_baseline, created_at
    """

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.registry_path = self.repo_root / "automation" / "control" / WORKTREE_REGISTRY

    # ── git helpers ────────────────────────────────────────────────

    def _run_git(self, args: list) -> str:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, check=True,
            cwd=str(self.repo_root),
        )
        return result.stdout.strip()

    def _run_git_in_wt(self, wt_path: Path, args: list) -> str:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, check=True,
            cwd=str(wt_path),
        )
        return result.stdout.strip()

    # ── validators ─────────────────────────────────────────────────

    def _validate_round_id(self, round_id: str) -> None:
        if not round_id or not round_id.startswith("R"):
            raise ValueError(f"Invalid round_id: {round_id}. Must start with 'R' (e.g. R030).")

    def _validate_purpose(self, purpose: str) -> None:
        if purpose not in VALID_PURPOSES:
            raise ValueError(f"Invalid purpose: {purpose}. Must be one of: {VALID_PURPOSES}")

    def _is_candidate_branch(self, branch: str) -> bool:
        return branch.startswith("work/candidate-")

    # ── worktree path ──────────────────────────────────────────────

    def get_worktree_path(self, round_id: str, purpose: str = "candidate") -> Path:
        """Get standardized worktree path: C:/stocktrade-<ROUND>-<PURPOSE>"""
        self._validate_round_id(round_id)
        self._validate_purpose(purpose)
        return WORKTREE_BASE / f"stocktrade-{round_id}-{purpose}"

    # ── lifecycle: create ──────────────────────────────────────────

    def create_worktree(self, round_id: str, branch: str, purpose: str = "candidate") -> Path:
        """Create isolated worktree from canonical baseline.

        Steps:
        1. Validate inputs (round_id format, purpose, candidate branch)
        2. Skip if worktree already exists (idempotent)
        3. Resolve canonical HEAD as baseline
        4. `git worktree add` from canonical HEAD
        5. Create candidate branch in the worktree
        6. Register in worktree_registry.json

        Returns the worktree path.
        """
        self._validate_round_id(round_id)
        self._validate_purpose(purpose)
        if not self._is_candidate_branch(branch):
            raise ValueError(f"Branch must be a candidate branch (work/candidate-*): {branch}")

        wt_path = self.get_worktree_path(round_id, purpose)

        # Idempotent: skip if already exists
        if wt_path.exists():
            logger.warning(f"Worktree {wt_path} already exists, reusing.")
            self._assert_branch_in_worktree(wt_path, branch)
            return wt_path

        # Resolve canonical HEAD as immutable baseline
        canonical_head = self._run_git(["rev-parse", "work/canonical-mainline-repair-001"])

        wt_path.mkdir(parents=True, exist_ok=True)
        self._run_git(["worktree", "add", str(wt_path), canonical_head])

        # Create candidate branch in the worktree
        self._run_git_in_wt(wt_path, ["checkout", "-b", branch])

        # Register lifecycle metadata
        self._register(round_id, purpose, str(wt_path), branch, canonical_head)

        logger.info(
            f"Created worktree: {wt_path}\n"
            f"  round={round_id} purpose={purpose}\n"
            f"  branch={branch}\n"
            f"  canonical_baseline={canonical_head}"
        )
        return wt_path

    # ── lifecycle: remove ──────────────────────────────────────────

    def remove_worktree(self, round_id: str, purpose: str = "candidate") -> None:
        """Remove (clean up) an isolated worktree after round closure.

        Uses git worktree remove (force if dirty).
        Removes registry entry after successful removal.
        """
        wt_path = self.get_worktree_path(round_id, purpose)
        if not wt_path.exists():
            logger.warning(f"Worktree {wt_path} does not exist, skipping removal.")
            self._unregister(round_id, purpose)
            return

        try:
            self._run_git(["worktree", "remove", str(wt_path)])
        except subprocess.CalledProcessError:
            logger.warning(f"Worktree {wt_path} is dirty, using --force remove.")
            self._run_git(["worktree", "remove", "--force", str(wt_path)])

        self._unregister(round_id, purpose)
        logger.info(f"Removed worktree {wt_path}")

    # ── baseline verification ──────────────────────────────────────

    def assert_clean_baseline(self, round_id: str, purpose: str = "candidate") -> None:
        """Assert worktree is based on current canonical HEAD.

        BLOCKER: If canonical has advanced since worktree creation,
        the worktree is stale and must be rebuilt.
        Raises ValueError on mismatch.
        """
        registry = self._load_registry()
        key = f"{round_id}_{purpose}"
        if key not in registry:
            raise ValueError(
                f"BLOCKER: No registry entry for {round_id}/{purpose}. "
                "Create worktree first with create_worktree()."
            )

        current_canonical = self._run_git(["rev-parse", "work/canonical-mainline-repair-001"])
        baseline = registry[key]["canonical_baseline"]

        if baseline != current_canonical:
            raise ValueError(
                f"BLOCKER (BLOCKER_B): Worktree {round_id}/{purpose} stale.\n"
                f"  canonical_baseline_at_creation: {baseline}\n"
                f"  current_canonical:              {current_canonical}\n"
                "  Rebuild worktree from latest canonical before proceeding."
            )

        logger.info(f"Baseline OK: {round_id}/{purpose} matches canonical {current_canonical}")

    def verify_baseline(self, round_id: str, purpose: str = "candidate") -> bool:
        """Non-blocking baseline check. Returns True if worktree is current."""
        try:
            self.assert_clean_baseline(round_id, purpose)
            return True
        except (ValueError, KeyError):
            return False

    # ── query ──────────────────────────────────────────────────────

    def list_active_worktrees(self) -> List[Dict[str, str]]:
        """List all active git worktrees."""
        result = self._run_git(["worktree", "list"])
        worktrees = []
        for line in result.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                entry = {"path": parts[0], "head": parts[1]}
                if len(parts) >= 3:
                    entry["branch"] = parts[2].strip("[]")
                worktrees.append(entry)
        return worktrees

    def list_registered(self) -> Dict[str, Any]:
        """List all worktrees in the local JSON registry."""
        return self._load_registry()

    def get_registered_for_round(self, round_id: str) -> Dict[str, Any]:
        """Get all registry entries for a given round_id."""
        registry = self._load_registry()
        return {
            k: v for k, v in registry.items()
            if v.get("round_id") == round_id
        }

    # ── registry persistence ───────────────────────────────────────

    def _register(self, round_id: str, purpose: str,
                  path: str, branch: str, canonical_baseline: str) -> None:
        registry = self._load_registry()
        key = f"{round_id}_{purpose}"
        registry[key] = {
            "round_id": round_id,
            "purpose": purpose,
            "path": path,
            "branch": branch,
            "canonical_baseline": canonical_baseline,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_registry(registry)

    def _unregister(self, round_id: str, purpose: str) -> None:
        registry = self._load_registry()
        key = f"{round_id}_{purpose}"
        registry.pop(key, None)
        self._save_registry(registry)

    def _load_registry(self) -> Dict[str, Any]:
        if self.registry_path.exists():
            with self.registry_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_registry(self, registry: Dict[str, Any]) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with self.registry_path.open("w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

    # ── internal helpers ───────────────────────────────────────────

    def _assert_branch_in_worktree(self, wt_path: Path, expected_branch: str) -> None:
        """Assert the worktree is on the expected branch (for idempotent reuse)."""
        current = self._run_git_in_wt(wt_path, ["rev-parse", "--abbrev-ref", "HEAD"])
        if current != expected_branch:
            raise ValueError(
                f"Worktree {wt_path} is on branch '{current}', expected '{expected_branch}'. "
                "Use a different branch name or remove the existing worktree."
            )
