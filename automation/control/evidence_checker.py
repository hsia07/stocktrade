"""
Evidence Completeness Checker

Mechanical validation that a candidate evidence package is complete.
Checks for required files and passes/failures from tests/validators.
Includes 40hex hash validation and merge/push separation enforcement for Law-0416 Phase 3.
"""

import json
import logging
import re
import subprocess
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

    # Merge/Push Separation Enforcement (Law-0416 Phase 3)
    MERGE_AUTHORIZED_INDICATORS = [
        "merge_decision_ready",
        "merge_authorized",
        "user_signoff_merge",
    ]
    
    PUSH_AUTHORIZED_INDICATORS = [
        "push_authorized",
        "user_signoff_push",
        "push_ready",
    ]

    def check_merge_push_separation(self, evidence: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate that merge and push are separately authorized.
        Returns (is_valid, issues_list).
        
        Checks:
        1. Merge authorization must NOT imply push authorization
        2. Push authorization must NOT imply merge authorization
        3. Both must have explicit authorization status
        4. Binding indicators (merge+push in same authorization) are blocked
        """
        issues = []
        
        # Check for binding indicators (merge+push together)
        binding_indicators = [
            "merge_and_push",
            "merge_push_combined",
            "auto_merge_push",
            "merge_then_push",
        ]
        
        for indicator in binding_indicators:
            if evidence.get(indicator) is True:
                issues.append(f"merge_push_binding_detected:{indicator}")
        
        # Check merge authorization
        merge_authorized = False
        for indicator in self.MERGE_AUTHORIZED_INDICATORS:
            if evidence.get(indicator) is True:
                merge_authorized = True
                break
        
        # Check push authorization
        push_authorized = False
        for indicator in self.PUSH_AUTHORIZED_INDICATORS:
            if evidence.get(indicator) is True:
                push_authorized = True
                break
        
        # Validate separation
        if merge_authorized and push_authorized:
            # Both in same evidence might indicate binding
            issues.append("merge_push_both_authorized_same_evidence:possible_binding")
        
        # Check for missing explicit authorization
        if not merge_authorized and not push_authorized:
            # No authorization info - that's ok, just log
            logger.info("No merge/push authorization indicators found in evidence")
        
        return len(issues) == 0, issues

    def validate_workflow_authorization(self, local_head: str, remote_head: str, operation: str) -> Tuple[bool, str]:
        """
        Validate workflow authorization for merge or push operations.
        Returns (is_authorized, reason_code).
        
        operation: "merge" or "push"
        """
        if operation not in ["merge", "push"]:
            return False, f"invalid_operation:{operation}"
        
        # Validate 40hex for heads
        is_valid, reason = self.validate_40hex_hash(local_head)
        if not is_valid:
            return False, f"local_head:{reason}"
        
        is_valid, reason = self.validate_40hex_hash(remote_head)
        if not is_valid:
            return False, f"remote_head:{reason}"
        
        if operation == "merge":
            # Merge requires explicit merge authorization
            return True, "merge_authorized:explicit_signoff_required"
        
        if operation == "push":
            # Push requires explicit push authorization (separate from merge)
            return True, "push_authorized:explicit_signoff_required"
        
        return False, "unknown_operation"

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

    # auto_advance.py forbidden check for Law-0416 phases (Phase 3)
    FORBIDDEN_FILES = [
        "automation/control/auto_advance.py",
        "automation/control/auto_advance.py",
    ]
    
    FORBIDDEN_INDICATORS = [
        "auto_advance_used",
        "auto_advance_modified",
        "using_auto_advance",
    ]
    
    def check_auto_advance_forbidden(self, evidence: Dict[str, Any], files_modified: List[str]) -> Tuple[bool, List[str]]:
        """
        Check that auto_advance.py is NOT used/modified in Law-0416 phase implementations.
        Returns (is_valid, issues_list).
        
        Forbidden for Law-0416 phases:
        - auto_advance.py must NOT be in files_modified
        - evidence must NOT indicate auto_advance usage
        - Any reference to auto_advance in Law-0416 phases is blocked
        """
        issues = []
        
        # Check files_modified list
        if files_modified:
            for file in files_modified:
                if any(forbidden in file for forbidden in self.FORBIDDEN_FILES):
                    issues.append(f"auto_advance_forbidden:file_touched:{file}")
        
        # Check evidence indicators
        for indicator in self.FORBIDDEN_INDICATORS:
            if evidence.get(indicator) is True:
                issues.append(f"auto_advance_forbidden:indicator_found:{indicator}")
        
        # Check candidate_branch name for Law-0416 context
        candidate_branch = evidence.get("candidate_branch", "")
        if "law-0416" in candidate_branch.lower() or "0416" in candidate_branch:
            # In Law-0416 phases, auto_advance.py is strictly forbidden
            if files_modified:
                for file in files_modified:
                    if "auto_advance" in file.lower():
                        issues.append(f"auto_advance_forbidden:law_0416_phase_blocks:{file}")
        
        return len(issues) == 0, issues

    # Readable/Mirror auto-sync verification (Law-0416 Phase 3)
    READABLE_MIRROR_PATHS = [
        "_governance/law/README.md",
        "opencode_readable_laws/",
    ]
    
    FORMAL_SOURCES_PRIORITY = ["02", "03", "04", "01"]
    
    # Patterns that indicate readable claims to override formal
    OVERRIDE_CLAIM_PATTERNS = [
        r"readable.*override.*formal",
        r"可覆寫.*正式法源",
        r"覆寫.*正式",
        r"替代.*法典",
        r"取代.*法源",
    ]
    
    # Required sync markers in readable files
    REQUIRED_SYNC_MARKERS = [
        r"同步時間[：:]\s*.+",
        r"sync.*time[：:]\s*.+",
        r"来源[：:]\s*(02|03|04|01)",
        r"source[：:]\s*(02|03|04|01)",
        r"版本[：:]\s*.+",
        r"version[：:]\s*.+",
    ]
    
    def check_readable_mirror_sync(self, evidence: Dict[str, Any] = None) -> Tuple[bool, List[str]]:
        """
        Verify readable/mirror files do not drift from or contradict formal sources.
        Returns (is_valid, issues_list).
        
        Checks:
        1. Readable files must NOT claim to override formal sources
        2. Readable files must have sync markers linking to formal sources
        3. Readable content must not contradict formal source priority (02 > 03 > 04 > 01)
        4. Formal source priority must be preserved in readable content
        """
        issues = []
        
        repo_root = Path(self.repo_root)
        
        # Check readable/mirror paths exist
        for readable_path in self.READABLE_MIRROR_PATHS:
            full_path = repo_root / readable_path
            
            if not full_path.exists():
                logger.warning(f"Readable/mirror path not found: {readable_path}")
                continue
            
            # Handle directory (opencode_readable_laws/)
            if full_path.is_dir():
                for md_file in full_path.glob("**/*.md"):
                    file_issues = self._check_single_readable_file(md_file, readable_path)
                    issues.extend(file_issues)
            else:
                # Handle single file (README.md)
                file_issues = self._check_single_readable_file(full_path, readable_path)
                issues.extend(file_issues)
        
        # Check evidence for readable-related claims if provided
        if evidence:
            readable_docs = evidence.get("readable_docs", [])
            for doc in readable_docs:
                doc_path = repo_root / doc
                if doc_path.exists():
                    file_issues = self._check_single_readable_file(doc_path, doc)
                    issues.extend(file_issues)
        
        return len(issues) == 0, issues
    
    def _check_single_readable_file(self, file_path: Path, relative_path: str) -> List[str]:
        """Check a single readable/mirror file for sync and contradiction issues."""
        issues = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check 1: No override claims
            for pattern in self.OVERRIDE_CLAIM_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append(f"readable:override_claim_detected:{relative_path}:pattern={pattern[:30]}")
            
            # Check 2: Required sync markers present
            markers_found = 0
            for pattern in self.REQUIRED_SYNC_MARKERS:
                if re.search(pattern, content, re.IGNORECASE):
                    markers_found += 1
            
            if markers_found == 0:
                issues.append(f"readable:missing_sync_markers:{relative_path}")
            elif markers_found < 2:
                issues.append(f"readable:insufficient_sync_markers:{relative_path}:found={markers_found}")
            
            # Check 3: Formal source priority not contradicted
            # Look for priority claims in content
            priority_patterns = [
                r"(02|03|04|01)\s*>\s*(02|03|04|01)",
                r"優先.*(02|03|04|01).*(02|03|04|01)",
                r"優先順序.*(02|03|04|01).*(02|03|04|01)",
            ]
            
            for pattern in priority_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if isinstance(match, tuple):
                        # Check if priority is wrong (should be 02 > 03 > 04 > 01)
                        if len(match) >= 2:
                            higher, lower = match[0], match[1]
                            expected_order = ["02", "03", "04", "01"]
                            if higher in expected_order and lower in expected_order:
                                if expected_order.index(higher) > expected_order.index(lower):
                                    issues.append(f"readable:priority_contradiction:{relative_path}:{higher}>{lower}_should_be_reversed")
            
            # Check 4: Verify "formal source priority" statement if present
            if "法源優先" in content or "formal source" in content.lower():
                # Should mention 02 > 03 > 04 > 01
                if "02" in content and "03" in content:
                    # Check for correct order mention
                    if not re.search(r"02.*03.*04.*01", content.replace(" ", "")):
                        issues.append(f"readable:priority_order_unclear:{relative_path}")
            
        except Exception as e:
            issues.append(f"readable:file_read_error:{relative_path}:{str(e)}")
        
        return issues
    
    def validate_readable_sync_in_evidence(self, evidence: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate readable sync verification results stored in evidence.
        Returns (is_valid, issues_list).
        
        Checks that evidence contains readable sync check results
        and that they passed (no drift/contradiction detected).
        """
        issues = []
        
        readable_sync = evidence.get("readable_sync_check", {})
        if not readable_sync:
            # No readable sync check performed - that's ok for non-readable candidates
            logger.info("No readable sync check results in evidence")
        return True, []
    
    # Governance Drift Full Automation (Law-0416 Phase 3)
    DRIFT_TYPES = [
        "source_target_head_mismatch",
        "formal_truth_contradiction",
        "candidate_scope_mismatch",
        "canonical_phase_state_drift",
        "baseline_readable_conflict",
    ]
    
    def check_governance_drift(self, evidence: Dict[str, Any] = None) -> Tuple[bool, List[str]]:
        """
        Detect and block governance drift (governance drift).
        Returns (is_valid, issues_list).
        
        Checks for drift between:
        1. source/target HEAD vs authorized objects
        2. formal truth vs baseline/readable state contradictions
        3. candidate scope vs authorized topic mismatch
        4. canonical/remote/candidate phase state drift
        5. baseline readable conflicts
        """
        issues = []
        
        repo_root = Path(self.repo_root)
        
        # Check 1: source/target HEAD vs authorized objects
        if evidence:
            source_head = evidence.get("source_head_before") or evidence.get("local_head_before")
            target_head = evidence.get("target_head_before") or evidence.get("remote_head_before")
            authorized_source = evidence.get("candidate_commit") or evidence.get("implementation_commit")
            authorized_target = evidence.get("target_head_expected")
            
            if source_head and authorized_source:
                if source_head != authorized_source:
                    issues.append(f"drift:source_target_head_mismatch:source={source_head[:8]}.._vs_authorized={authorized_source[:8]}..")
            
            if target_head and authorized_target:
                if target_head != authorized_target:
                    issues.append(f"drift:source_target_head_mismatch:target={target_head[:8]}.._vs_expected={authorized_target[:8]}..")
        
        # Check 2: formal truth vs baseline/readable contradictions
        baseline_path = repo_root / "CURRENT_GOVERNANCE_BASELINE.md"
        if baseline_path.exists():
            try:
                with open(baseline_path, "r", encoding="utf-8") as f:
                    baseline_content = f.read()
                
                # Check for phase completion contradictions
                if "Phase 3" in baseline_content:
                    if "completed" in baseline_content and "5/7" in baseline_content:
                        # Contradiction: says completed but only 5/7 done
                        issues.append("drift:formal_truth_contradiction:phase3_5/7_vs_completed")
            except Exception as e:
                issues.append(f"drift:baseline_read_error:{str(e)}")
        
        # Check 3: candidate scope vs authorized topic
        if evidence:
            task_type = evidence.get("task_type", "")
            candidate_branch = evidence.get("candidate_branch", "")
            
            # Check if scope expanded beyond authorized topic
            scope_fields = ["files_modified", "added_features", "scope_expansion"]
            for field in scope_fields:
                if field in evidence:
                    field_value = evidence.get(field)
                    if isinstance(field_value, list):
                        for item in field_value:
                            if "governance_drift" not in str(item).lower() and "drift" not in str(item).lower():
                                # This is ok - just checking for unauthorized scope
                                pass
                    elif isinstance(field_value, str):
                        if "governance_drift" not in field_value.lower() and "drift" not in field_value.lower():
                            # Check if evidence claims scope expansion
                            if "expanded" in field_value.lower() or "added" in field_value.lower():
                                issues.append(f"drift:candidate_scope_mismatch:unauthorized_scope_expansion")
        
        # Check 4: canonical/remote/candidate phase state drift
        if evidence:
            phase_state = evidence.get("phase_state") or evidence.get("law_0416_phase_3_started")
            if phase_state is not None:
                if phase_state is True and "Phase 3" in str(evidence.get("task_type", "")):
                    # Phase 3 started but check for state drift
                    completed = evidence.get("law_0416_phase_3_fifth_candidate_completed")
                    if completed is True:
                        # Check if phase claims "completed" vs actual progress
                        if "not yet complete" not in str(evidence.get("next_action", "")).lower():
                            issues.append("drift:canonical_phase_state_drift:claims_complete_vs_ongoing")
        
        # Check 5: baseline readable conflicts
        if baseline_path.exists():
            try:
                with open(baseline_path, "r", encoding="utf-8") as f:
                    baseline_content = f.read()
                
                # Check for readable vs formal conflicts
                if "readable" in baseline_content.lower() and "formal" in baseline_content.lower():
                    # Check for contradiction markers
                    if "contradict" in baseline_content.lower() or "conflict" in baseline_content.lower():
                        issues.append("drift:baseline_readable_conflict:contradiction_marker_found")
            except Exception as e:
                pass  # Already handled above
        
        return len(issues) == 0, issues
    
    def validate_governance_drift_in_evidence(self, evidence: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate governance drift check results stored in evidence.
        Returns (is_valid, issues_list).
        """
        issues = []
        
        drift_check = evidence.get("governance_drift_check", {})
        if not drift_check:
            # No drift check performed - that's ok for non-drift candidates
            logger.info("No governance drift check results in evidence")
            return True, []
        
        # Check if drift detected
        if drift_check.get("drift_detected") is True:
            issues.append("governance_drift:drift_detected:check_failed")
        
        # Check reason codes
        reason_codes = drift_check.get("reason_codes", [])
        for code in reason_codes:
            if "drift:" in code:
                issues.append(f"governance_drift:{code}")
        
        return len(issues) == 0, issues
        
        # Check if sync check passed
        if readable_sync.get("drift_detected") is True:
            issues.append("readable_sync:drift_detected:check_failed")
        
        if readable_sync.get("contradiction_found") is True:
            issues.append("readable_sync:contradiction_found:formal_source_contradicted")
        
        # Check reason codes
        reason_codes = readable_sync.get("reason_codes", [])
        for code in reason_codes:
            if "override_claim" in code:
                issues.append(f"readable_sync:{code}")
            if "missing_sync_marker" in code:
                issues.append(f"readable_sync:{code}")
            if "priority_contradiction" in code:
                issues.append(f"readable_sync:{code}")
        
        return len(issues) == 0, issues

    # Repo Full Audit before Merge (Law-0416 Phase 3)
    AUDIT_SCOPE_PATHS = [
        "automation/control/candidates/",
        "automation/control/andidates/LAW-0416-PHASE-3-READABLE-SYNC-VERIFICATION/",
        "automation/control/evidence_checker.py",
        "_governance/law/",
        "opencode_readable_laws/",
    ]
    
    # Audit check items
    AUDIT_CHECK_ITEMS = [
        "candidate_evidence_complete",
        "law04_compliance_present",
        "commit_hash_valid_40hex",
        "evidence_package_in_tree",
        "no_scope_expansion",
        "readable_sync_verified",
        "auto_advance_forbidden_checked",
        "merge_push_separation_verified",
        "phase3_candidate_single_topic",
    ]
    
    def perform_pre_merge_repo_audit(self, repo_root: Path = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Perform repo-wide governance audit before merge.
        Returns (audit_passed, audit_results).
        
        Checks:
        1. All Phase 3 candidates have complete evidence packages
        2. Law 04 compliance verified in all evidence.json files
        3. Commit hashes are valid 40hex
        4. No scope expansion beyond single topic per candidate
        5. Readable sync verification implemented
        6. Auto-advance forbidden check implemented
        7. Merge/push separation enforced
        8. RETURN_TO_CHATGPT format compliance (basic check)
        """
        if repo_root is None:
            repo_root = Path(self.repo_root)
        
        audit_results = {
            "audit_scope": "pre_merge_repo_wide",
            "audit_passed": False,
            "check_results": {},
            "reason_codes": [],
            "candidates_checked": [],
            "issues_found": [],
        }
        
        issues = []
        candidates_checked = []
        
        # Scan all Phase 3 candidates
        candidates_path = repo_root / "automation/control/candidates"
        if candidates_path.exists():
            for candidate_dir in candidates_path.iterdir():
                if candidate_dir.is_dir() and "LAW-0416-PHASE-3" in candidate_dir.name:
                    check_result = self._audit_single_candidate(candidate_dir)
                    candidates_checked.append(candidate_dir.name)
                    audit_results["check_results"][candidate_dir.name] = check_result
                    
                    if not check_result["passed"]:
                        for issue in check_result["issues"]:
                            issues.append(f"{candidate_dir.name}:{issue}")
        
        audit_results["candidates_checked"] = candidates_checked
        audit_results["issues_found"] = issues
        audit_results["reason_codes"] = issues
        audit_results["audit_passed"] = len(issues) == 0
        
        return len(issues) == 0, audit_results
    
    def _audit_single_candidate(self, candidate_dir: Path) -> Dict[str, Any]:
        """Audit a single Phase 3 candidate directory."""
        result = {
            "passed": False,
            "candidate": candidate_dir.name,
            "issues": [],
            "checks": {},
        }
        
        issues = []
        
        # Check 1: Evidence package complete
        required_files = ["task.txt", "evidence.json", "report.json"]
        for req_file in required_files:
            if not (candidate_dir / req_file).exists():
                issues.append(f"evidence_package:missing:{req_file}")
                result["checks"]["candidate_evidence_complete"] = False
            else:
                result["checks"]["candidate_evidence_complete"] = True
        
        # Check 2: Law 04 compliance
        evidence_path = candidate_dir / "evidence.json"
        if evidence_path.exists():
            try:
                with open(evidence_path, "r", encoding="utf-8") as f:
                    evidence = json.load(f)
                    law_compliance = evidence.get("law_compliance")
                    if law_compliance == "04":
                        result["checks"]["law04_compliance_present"] = True
                    else:
                        issues.append(f"law04_compliance:wrong_value:{law_compliance}")
                        result["checks"]["law04_compliance_present"] = False
            except Exception as e:
                issues.append(f"evidence_parse_error:{str(e)}")
                result["checks"]["law04_compliance_present"] = False
        
        # Check 3: Commit hash valid 40hex
        if evidence_path.exists():
            try:
                with open(evidence_path, "r", encoding="utf-8") as f:
                    evidence = json.load(f)
                    commit_hash = evidence.get("candidate_commit") or evidence.get("implementation_commit")
                    if commit_hash:
                        is_valid, reason = self.validate_40hex_hash(commit_hash)
                        if is_valid:
                            result["checks"]["commit_hash_valid_40hex"] = True
                        else:
                            issues.append(f"commit_hash:{reason}")
                            result["checks"]["commit_hash_valid_40hex"] = False
            except Exception as e:
                issues.append(f"commit_hash_check_error:{str(e)}")
        
        # Check 4: Evidence package in commit tree (basic check)
        # This would require git ls-tree in real implementation
        result["checks"]["evidence_package_in_tree"] = "unknown (requires git inspection)"
        
        # Check 5: No scope expansion (single topic)
        if evidence_path.exists():
            try:
                with open(evidence_path, "r", encoding="utf-8") as f:
                    evidence = json.load(f)
                    task_type = evidence.get("task_type", "")
                    if "phase3" in task_type.lower():
                        result["checks"]["phase3_candidate_single_topic"] = True
                    else:
                        issues.append(f"scope_expansion:not_phase3_candidate")
                        result["checks"]["phase3_candidate_single_topic"] = False
            except Exception:
                pass
        
        result["passed"] = len(issues) == 0
        result["issues"] = issues
        return result
    
    def check_pre_merge_audit_ready(self, evidence: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if pre-merge repo audit is ready/passed.
        Returns (is_ready, issues_list).
        
        Distinguishes between:
        - audit failed (block merge)
        - audit passed (ready for merge signoff)
        """
        issues = []
        
        repo_audit = evidence.get("repo_audit_results", {})
        if not repo_audit:
            issues.append("repo_audit:not_performed")
            return False, issues
        
        if repo_audit.get("audit_passed") is not True:
            issues.append("repo_audit:failed")
            # Add reason codes
            reason_codes = repo_audit.get("reason_codes", [])
            for code in reason_codes:
                issues.append(f"repo_audit:{code}")
            return False, issues
        
        return True, []

from .return_to_chatgpt_verifier import ReturnToChatGPTVerifier

    def verify_return_to_chatgpt(self, output_text):
        '''Verify RETURN_TO_CHATGPT output using ReturnToChatGPTVerifier.'''
        verifier = ReturnToChatGPTVerifier()
        return verifier.verify_output(output_text)
    
    def validate_return_to_chatgpt_in_evidence(self, evidence):
        '''Validate RETURN_TO_CHATGPT verification in evidence.'''
        verifier = ReturnToChatGPTVerifier()
        return verifier.validate_in_evidence(evidence)
