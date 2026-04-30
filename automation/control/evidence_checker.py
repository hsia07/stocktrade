"""
Evidence Completeness Checker

Mechanical validation that a candidate evidence package is complete.
Checks for required files and passes/failures from tests/validators.
"""

import json
import logging
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
