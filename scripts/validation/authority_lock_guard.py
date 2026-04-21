#!/usr/bin/env python3
"""
Authority Lock Guard - Prevents wrong topic source precedence

AUTHORITY RULES:
- Topic authority: MUST read from _governance/law/161輪正式重編主題總表_唯一基準版_v2.md
- Validation authority: MUST read from _governance/law/03_161輪逐輪施行細則法典_整合法條增補版.docx

EXCLUDED SOURCES (cannot be used as topic authority):
- opencode_readable_laws/*.md (mirror only)
- 05_每輪詳細主題補充法典_機器可執行補充版.md (supplement only)
- _governance/law/readable/03* (mirror only)
- Any historical draft or archive files
- User instruction / verbal instruction
- Chat history summaries
"""

import sys
import os
import hashlib
import re

AUTHORITATIVE_TOPIC_FILE = "_governance/law/161輪正式重編主題總表_唯一基準版_v2.md"
AUTHORITATIVE_VALIDATION_FILE = "_governance/law/03_161輪逐輪施行細則法典_整合法條增補版.docx"

EXCLUDED_PATTERNS = [
    "opencode_readable_laws/",
    "_governance/law/readable/03",
    "05_每輪詳細主題補充法典",
    "archive",
    "historical",
    "_backup",
    "_draft"
]

def compute_hash(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()[:16]

def is_excluded_path(filepath):
    filepath_lower = filepath.lower()
    for pattern in EXCLUDED_PATTERNS:
        if pattern.lower() in filepath_lower:
            return True
    return False

def validate_authority_source(module_name, caller_filepath=None):
    """Validate that the correct authority file is being used."""
    errors = []
    
    if not os.path.exists(AUTHORITATIVE_TOPIC_FILE):
        errors.append(f"TOPIC AUTHORITY MISSING: {AUTHORITATIVE_TOPIC_FILE}")
    
    if not os.path.exists(AUTHORITATIVE_VALIDATION_FILE):
        errors.append(f"VALIDATION AUTHORITY MISSING: {AUTHORITATIVE_VALIDATION_FILE}")
    
    if caller_filepath and is_excluded_path(caller_filepath):
        errors.append(f"EXCLUDED SOURCE USED: {caller_filepath} - cannot be used as topic authority")
    
    if errors:
        print("[AUTHORITY LOCK VIOLATION]", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return False
    
    print(f"[AUTHORITY LOCK] TOPIC: {AUTHORITATIVE_TOPIC_FILE}")
    print(f"[AUTHORITY LOCK] VALIDATION: {AUTHORITATIVE_VALIDATION_FILE}")
    return True

def get_round_topic_from_v2(round_id):
    """Extract topic for a specific round from v2."""
    if not os.path.exists(AUTHORITATIVE_TOPIC_FILE):
        return None
    
    with open(AUTHORITATIVE_TOPIC_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    pattern = rf"\| {round_id} \| ([^|]+) \| ([^|]+) \|"
    match = re.search(pattern, content)
    if match:
        return match.group(2).strip()
    return None

def main():
    if len(sys.argv) > 1:
        module_name = sys.argv[1]
        caller_filepath = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        module_name = "governance_lock"
        caller_filepath = None
    
    if not validate_authority_source(module_name, caller_filepath):
        sys.exit(1)
    
    print(f"[authority_lock_guard] Module: {module_name}")
    print(f"[authority_lock_guard] Status: PASS")

if __name__ == "__main__":
    main()