#!/usr/bin/env python3
"""
check_required_evidence.py - Enhanced version with content validation
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import yaml

def check_evidence_content(evidence_path: Path) -> tuple:
    """Check that evidence.json contains real work indicators, not packaging."""
    try:
        data = json.loads(evidence_path.read_text(encoding="utf-8"))
        
        # Check status is not invalidated
        if data.get("status") == "INVALIDATED":
            return False, "EVIDENCE_MARKED_INVALIDATED"
        
        # Check for work_done with actual content
        work_done = data.get("work_done", [])
        if isinstance(work_done, list):
            if len(work_done) == 0:
                return False, "NO_WORK_DONE_ITEMS"
            # Check if all items are just packaging descriptions
            packaging_only = all(
                any(x in str(item).lower() for x in ["evidence", "report", "validated", "structure"])
                for item in work_done
            )
            if packaging_only:
                return False, "PACKAGING_ONLY_WORK_ITEMS"
        
        # Check validation is not fake
        validation = data.get("validation", "")
        if validation == "INVALIDATED":
            return False, "VALIDATION_INVALIDATED"
        
        # Check formal_status_code
        formal_status = data.get("formal_status_code", "")
        if "FALSE" in str(formal_status).upper() or "INVALIDATED" in str(formal_status).upper():
            return False, "FORMAL_STATUS_FALSE_CANDIDATE"
        
        return True, "EVIDENCE_CONTENT_VALID"
    except Exception as e:
        return False, f"EVIDENCE_PARSE_ERROR: {e}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()
    
    manifest = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))
    missing = []
    invalid_content = []
    
    for item in manifest.get("required_evidence", []):
        path = Path(item)
        if not path.exists():
            missing.append(item)
        elif "evidence.json" in item:
            # Extra validation for evidence.json content
            valid, reason = check_evidence_content(path)
            if not valid:
                invalid_content.append(f"{item}: {reason}")
    
    if missing:
        print("FAIL: missing required evidence")
        for m in missing:
            print(" -", m)
        sys.exit(1)
    
    if invalid_content:
        print("FAIL: evidence content validation failed")
        for i in invalid_content:
            print(" -", i)
        sys.exit(1)
    
    print("PASS: required evidence present and content valid")

if __name__ == "__main__":
    main()