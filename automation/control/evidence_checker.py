"""
Evidence Completeness Checker

Mechanical validation that a candidate evidence package is complete.
Checks for required files and passes/failures from tests/validators.
Includes 40hex hash validation for Law-0416 Phase 3.
"""

import json
import logging
import re
from pathlib import Path
from typing import Tuple, List, Dict, Any

logger = logging.getLogger("evidence_checker")


class Law04ComplianceError(Exception):
    """Raised when Law 04 compliance check fails."""
    pass


class EvidenceChecker:
    """Check evidence completeness for candidate auto-advance."""

    REQUIRED_FILES = [
        "task.txt",
        "report.json",
        "evidence.json",
    ]

    OPTIONAL_FILES = [
        "candidate.diff",
    ]

    REQUIRED_LAW_COMPLIANCE = "04"  # Law 04 compliance value

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent

    def check_completeness(self, candidate_dir: Path) -> Tuple[bool, List[str]]:
        """
        Return (complete, missing_items).
        Checks required files exist and report.json contains pass indicators.
        """
        missing = []

        # Check required files
        for filename in self.REQUIRED_FILES:
            file_path = candidate_dir / filename
            if not file_path.exists():
                missing.append(f"missing:{filename}")

        # Check report.json for validation results
        report_path = candidate_dir / "report.json"
        if report_path.exists():
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    report = json.load(f)
                if report.get("status") != "completed":
                    missing.append("report_status_not_completed")
                if report.get("formal_status_code") == "blocked":
                    missing.append("report_formal_status_blocked")
            except Exception as e:
                missing.append(f"report_parse_error:{e}")
        else:
            missing.append("missing:report.json")

        # Check evidence.json
        evidence_path = candidate_dir / "evidence.json"
        if evidence_path.exists():
            try:
                with open(evidence_path, "r", encoding="utf-8") as f:
                    evidence = json.load(f)
                # Check test results if present
                tests = evidence.get("test_results", {})
                if tests.get("failed", 0) > 0:
                    missing.append(f"tests_failed:{tests['failed']}")
                
                # Law 04 compliance check (required by Law 04 Article 261)
                law_compliance = evidence.get("law_compliance")
                if law_compliance is None:
                    missing.append("law_compliance:missing")
                elif law_compliance != self.REQUIRED_LAW_COMPLIANCE:
                    missing.append(f"law_compliance:wrong_value:{law_compliance}")
                
                # 40hex validation: candidate_commit must be valid 40hex
                candidate_commit = evidence.get("candidate_commit") or evidence.get("commit_hash")
                if candidate_commit:
                    is_valid, reason = self.validate_40hex_hash(candidate_commit)
                    if not is_valid:
                        missing.append("candidate_commit:" + reason)
                
                # 40hex validation: baseline_sync_commit if present
                baseline_commit = evidence.get("baseline_sync_commit")
                if baseline_commit:
                    is_valid, reason = self.validate_40hex_hash(baseline_commit)
                    if not is_valid:
                        missing.append("baseline_sync_commit:" + reason)
                
                # Check merge_decision_ready if present
                if evidence.get("merge_decision_ready") is True:
                    if law_compliance != self.REQUIRED_LAW_COMPLIANCE:
                        missing.append("merge_decision_ready:blocked_without_law04_compliance")
                        
            except Exception as e:
                missing.append(f"evidence_parse_error:{e}")
        else:
            missing.append("missing:evidence.json")

        complete = len(missing) == 0
        if not complete:
            logger.warning(f"Evidence incomplete: {missing}")
        return complete, missing

    def check_tests_and_validators(self, evidence: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Check test/validator pass summary from evidence dict."""
        issues = []
        tests = evidence.get("test_results", {})
        if tests:
            total = tests.get("total_tests", 0)
            passed = tests.get("passed", 0)
            failed = tests.get("failed", 0)
            if failed > 0:
                issues.append(f"tests_failed:{failed}/{total}")
            if passed < total:
                issues.append(f"tests_incomplete:{passed}/{total}")

        validators = evidence.get("validator_results", {})
        if validators:
            for name, result in validators.items():
                if result != "PASS":
                    issues.append(f"validator_fail:{name}={result}")

        return len(issues) == 0, issues

    def validate_40hex_hash(self, hash_str: str) -> Tuple[bool, str]:
        """
        Validate that a string is a valid 40hex git commit hash.
        Returns (is_valid, reason_code).
        
        Checks:
        1. Must be exactly 40 characters
        2. Must contain only hex characters (0-9, a-f, A-F)
        3. Must correspond to a real git object in the repository
        """
        if not hash_str or not isinstance(hash_str, str):
            return False, "hash_empty_or_not_string"
        
        # Check length (must be exactly 40)
        if len(hash_str) != 40:
            return False, f"hash_length_not_40:actual_len={len(hash_str)}"
        
        # Check hex-only (only 0-9, a-f, A-F)
        if not re.match(r'^[0-9a-fA-F]{40}$', hash_str):
            return False, "hash_not_40hex:contains_non_hex_chars"
        
        # Check if hash corresponds to a real git object
        try:
            import subprocess
            result = subprocess.run(
                ["git", "cat-file", "-t", hash_str],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                timeout=5
            )
            if result.returncode == 0:
                return True, "hash_valid_40hex_git_object_exists"
            else:
                return False, "hash_not_found:not_a_valid_git_object"
        except Exception as e:
            return False, f"hash_validation_error:{str(e)}"

    def validate_evidence_hashes(self, evidence: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate all commit hashes in evidence.json are valid 40hex.
        Checks: candidate_commit, baseline_sync_commit, commit_hash, etc.
        """
        issues = []
        
        # List of hash fields to validate
        hash_fields = [
            ("candidate_commit", "candidate_commit"),
            ("baseline_sync_commit", "baseline_sync_commit"),
            ("commit_hash", "commit_hash"),
            ("source_head_before", "source_head_before"),
            ("target_head_before", "target_head_before"),
            ("target_head_after", "target_head_after"),
            ("local_head_before", "local_head_before"),
            ("remote_head_before", "remote_head_before"),
            ("remote_head_after", "remote_head_after"),
        ]
        
        for field_name, display_name in hash_fields:
            hash_value = evidence.get(field_name)
            if hash_value:
                is_valid, reason = self.validate_40hex_hash(hash_value)
                if not is_valid:
                    issues.append(f"{display_name}:{reason}")
        
        return len(issues) == 0, issues
