"""
RETURN_TO_CHATGPT Output Verification (Law-0416 Phase 3 - 7th candidate)
Machine-checkable verification of RETURN_TO_CHATGPT output format compliance.
Only does verification/blocking, NOT auto-rewrite or auto-correction.
"""

import json
import re
from typing import Tuple, List, Dict, Any


class ReturnToChatGPTVerifier:
    """Verify RETURN_TO_CHATGPT output format compliance."""
    
    REQUIRED_FIELDS = [
        "status",
        "formal_status_code",
        "task_type",
        "current_branch",
        "actual_head_commit_hash",
        "actual_head_commit_hash_valid_40hex_true_or_false",
        "working_tree_clean_before_merge_true_or_false",
        "local_merge_completed_true_or_false",
        "merge_commit_hash",
        "merge_commit_hash_valid_40hex_true_or_false",
        "push_executed_true_or_false",
        "promote_executed_true_or_false",
        "pr_created_true_or_false",
        "validation_summary",
        "final_conclusion",
        "next_action",
    ]
    
    def verify_output(self, output_text):
        """
        Verify RETURN_TO_CHATGPT output format compliance.
        Returns (is_valid, issues_list).
        """
        issues = []
        
        if not output_text or not isinstance(output_text, str):
            issues.append("return_to_chatgpt:missing_output")
            return False, issues
        
        # Check 1: Formal body presence
        if "RETURN_TO_CHATGPT" not in output_text:
            issues.append("return_to_chatgpt:formal_body_missing")
            return False, issues
        
        # Extract RETURN_TO_CHATGPT section
        rtc_start = output_text.find("RETURN_TO_CHATGPT")
        if rtc_start == -1:
            issues.append("return_to_chatgpt:formal_body_not_found")
            return False, issues
        
        # Get text before and after RETURN_TO_CHATGPT
        preamble = output_text[:rtc_start]
        rtc_section = output_text[rtc_start:]
        
        # Check 2: Preamble NOT more complete than formal body
        preamble_lines = [line for line in preamble.split('\n') if line.strip()]
        rtc_lines = [line for line in rtc_section.split('\n') if line.strip()]
        
        # If preamble has significantly more content than RETURN_TO_CHATGPT section
        if len(preamble_lines) > len(rtc_lines) * 1.5:
            issues.append("return_to_chatgpt:preamble_more_complete_than_formal_body")
        
        # Check 3: Required fields presence (if JSON format)
        if "{" in rtc_section and "}" in rtc_section:
            try:
                # Try to extract JSON block
                json_start = rtc_section.find("{")
                json_end = rtc_section.rfind("}") + 1
                if json_start != -1 and json_end != -1:
                    json_str = rtc_section[json_start:json_end]
                    parsed = json.loads(json_str)
                    
                    # Check required fields
                    for field in self.REQUIRED_FIELDS:
                        if field not in parsed:
                            issues.append("return_to_chatgpt:missing_required_field:" + field)
                        elif parsed[field] is None or parsed[field] == '':
                            issues.append("return_to_chatgpt:empty_required_field:" + field)
                    
                    # Check 4: Field contradictions
                    if "push_executed" in parsed and "push_executed_true_or_false" in parsed:
                        if parsed["push_executed"] is True and parsed["push_executed_true_or_false"] is False:
                            issues.append("return_to_chatgpt:field_contradiction:push_executed")
                
            except json.JSONDecodeError as e:
                issues.append("return_to_chatgpt:json_parse_error:" + str(e))
            except Exception as e:
                issues.append("return_to_chatgpt:verification_error:" + str(e))
        
        return len(issues) == 0, issues
    
    def validate_in_evidence(self, evidence):
        """
        Validate RETURN_TO_CHATGPT verification results stored in evidence.
        Returns (is_valid, issues_list).
        """
        issues = []
        
        rtc_check = evidence.get("return_to_chatgpt_verification", {})
        if not rtc_check:
            # No RETURN_TO_CHATGPT check performed - that's ok for non-RTC candidates
            return True, []
        
        # Check if verification passed
        if rtc_check.get("verification_passed") is not True:
            issues.append("return_to_chatgpt:verification_failed")
        
        # Check reason codes
        reason_codes = rtc_check.get("reason_codes", [])
        for code in reason_codes:
            if "return_to_chatgpt:" in code:
                issues.append("return_to_chatgpt:" + code)
        
        return len(issues) == 0, issues
