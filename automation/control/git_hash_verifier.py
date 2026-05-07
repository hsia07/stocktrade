"""
Git Hash Auto-Extraction & Verification Module (BLOCKER_A remediation)

Resolves auto mode BLOCKER_A: RETURN_TO_CHATGPT commit hash transcription errors.
All commit hashes are extracted directly from git truth via `git rev-parse HEAD`.
NO manual transcription of commit hashes in RETURN_TO_CHATGPT output.
Machine-checkable: hash reported = git HEAD hash, verified programmatically.

Usage:
    from automation.control.git_hash_verifier import GitHashVerifier
    verifier = GitHashVerifier()
    head = verifier.get_head_hash()              # auto-extracted from git
    is_match = verifier.verify_hash(head)         # self-check
    verifier.assert_hash_matches(head)            # raises ValueError on mismatch
    data = verifier.get_report_data()             # structured for RETURN_TO_CHATGPT
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("git_hash_verifier")


class GitHashVerifier:
    """Auto-extract and verify git commit hashes from git truth (never manual input)."""

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent

    def _run_git(self, args: list) -> str:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, check=True,
            cwd=str(self.repo_root),
        )
        return result.stdout.strip()

    def get_head_hash(self) -> str:
        """Auto-extract HEAD full 40-hex hash from git truth. NEVER from manual input."""
        return self._run_git(["rev-parse", "HEAD"])

    def get_short_hash(self, length: int = 7) -> str:
        """Get abbreviated hash for display only. Use get_head_hash() for verification."""
        return self._run_git(["rev-parse", f"--short={length}", "HEAD"])

    def get_ref_hash(self, ref: str) -> str:
        """Resolve any git ref to its full 40-hex hash."""
        return self._run_git(["rev-parse", ref])

    def verify_hash(self, reported_hash: str) -> bool:
        """Machine-check: does reported_hash exactly equal actual HEAD hash?

        This is the core verification method that eliminates manual transcription errors.
        Returns True only if reported_hash matches git rev-parse HEAD.
        """
        actual = self.get_head_hash()
        return reported_hash == actual

    def verify_ref(self, ref: str, expected_hash: str) -> bool:
        """Verify a named ref (branch, tag) resolves to expected_hash."""
        actual = self.get_ref_hash(ref)
        return actual == expected_hash

    def assert_hash_matches(self, reported_hash: str) -> None:
        """Assert reported hash matches HEAD. Raises ValueError on mismatch.

        Use this at the end of candidate creation to self-check:
            verifier.assert_hash_matches(reported_hash)
        If the hash was manually transcribed instead of auto-extracted,
        this will raise ValueError with clear error message.
        """
        actual = self.get_head_hash()
        if reported_hash != actual:
            raise ValueError(
                f"HASH MISMATCH (BLOCKER_A): reported={reported_hash} actual={actual}\n"
                f"Manual hash transcription detected or commit was amended after hash was recorded.\n"
                f"FIX: Use GitHashVerifier.get_head_hash() to auto-extract hash into RETURN_TO_CHATGPT."
            )

    def assert_ref_matches(self, ref: str, expected_hash: str) -> None:
        """Assert a named ref resolves to expected_hash. Raises ValueError on mismatch."""
        actual = self.get_ref_hash(ref)
        if actual != expected_hash:
            raise ValueError(
                f"REF MISMATCH: {ref} expected={expected_hash} actual={actual}\n"
                f"Branch may have been updated since hash was recorded."
            )

    def is_valid_40hex(self, hash_str: str) -> bool:
        """Check if string is a valid 40-character hexadecimal commit hash."""
        if not hash_str or len(hash_str) != 40:
            return False
        return all(c in "0123456789abcdef" for c in hash_str)

    def get_report_data(self) -> Dict[str, Any]:
        """Generate structured hash data for RETURN_TO_CHATGPT auto-insertion.

        Returns a dict with:
          - commit_hash: auto-extracted from git rev-parse HEAD
          - commit_hash_valid_40hex: verified 40-hex check
          - commit_hash_source: always 'auto_extracted_from_git_rev_parse_HEAD'
          - commit_hash_manual_transcription: always False
        """
        head = self.get_head_hash()
        return {
            "commit_hash": head,
            "commit_hash_valid_40hex": self.is_valid_40hex(head),
            "commit_hash_source": "auto_extracted_from_git_rev_parse_HEAD",
            "commit_hash_manual_transcription": False,
        }
