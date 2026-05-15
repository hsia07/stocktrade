#!/usr/bin/env python3
"""
Aider / OpenCode Mechanical Constraints Validator

Checks that Aider governance rules exist and are referenceable.
This validator checks for the PRESENCE of constraint documentation,
not runtime enforcement (which is in hooks/validators).

Checks:
1. Aider path resolution rules exist in governance suite
2. Ambiguous path block rules exist
3. Small task split / load limit rules exist
4. Prohibited paths rules exist
5. Hook fail must not use --no-verify rule exists
6. OpenCode must not self-authorize additional powers
7. Runtime / governance operation isolation rules exist
8. If only doc-exists check possible, reports PARTIAL not COMPLETE
"""

import argparse
import sys
from pathlib import Path


OPencode_BRIDGE_DIR = (
    Path("_governance")
    / "stocktrade_autonomy_governance_suite"
    / "09_OPENCODE_BRIDGE"
)

REQUIRED_RULE_SECTIONS = [
    "Aider 路徑解析規則",
    "Aider 小任務拆分規則",
    "Aider 負荷上限規則",
    "Aider 禁止操作規則",
    "Hook 失敗處理規則",
    "OpenCode 權限限制",
    "Runtime 與治理操作隔離",
]

SECURITY_RULE_PATTERNS = [
    "ambiguous path",
    "task split",
    "load limit",
    "prohibited path",
    "no-verify",
    "self-authorize",
    "segregat",
    "isolat",
]


def check_governance_rules_file() -> tuple:
    errors = []
    partials = []

    if not OPencode_BRIDGE_DIR.exists():
        errors.append(
            f"OpenCode bridge directory not found: {OPencode_BRIDGE_DIR}"
        )
        return errors, partials

    aider_rules_file = OPencode_BRIDGE_DIR / "04_aider_governance_rules.md"
    if not aider_rules_file.exists():
        errors.append(
            f"Aider governance rules file not found: {aider_rules_file}"
        )
        return errors, partials

    content = aider_rules_file.read_text(encoding="utf-8", errors="replace")

    for section in REQUIRED_RULE_SECTIONS:
        if section not in content:
            partials.append(
                f"Required rule section not found: {section} (documentation gap)"
            )

    for pattern in SECURITY_RULE_PATTERNS:
        if pattern not in content.lower():
            partials.append(
                f"Security rule pattern not found in doc: '{pattern}' (documentation gap)"
            )

    if partials:
        return errors, partials

    if not partials:
        return errors, partials

    return errors, partials


def check_aider_configuration() -> tuple:
    errors = []
    partials = []

    dot_aider_conf = Path(".aider.conf.yml")
    aider_conf = Path("aider.conf.yml")
    if not dot_aider_conf.exists() and not aider_conf.exists():
        partials.append("No aider configuration file found (.aider.conf.yml or aider.conf.yml)")

    return errors, partials


def check_hook_integrity() -> tuple:
    errors = []
    partials = []

    githooks_dir = Path(".githooks")
    if not githooks_dir.exists():
        errors.append(".githooks directory not found")
        return errors, partials

    pre_commit = githooks_dir / "pre-commit"
    pre_push = githooks_dir / "pre-push"
    pre_push_ps1 = githooks_dir / "pre-push.ps1"

    if not pre_commit.exists():
        errors.append("pre-commit hook not found")
    if not pre_push.exists() and not pre_push_ps1.exists():
        errors.append("pre-push hook not found")

    hooks_path_setting = None
    import subprocess
    try:
        result = subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            hooks_path_setting = result.stdout.strip()
    except Exception:
        partials.append("Cannot verify git core.hooksPath setting")

    if hooks_path_setting != ".githooks":
        partials.append(
            f"git core.hooksPath is '{hooks_path_setting}', expected '.githooks'"
        )

    return errors, partials


def main():
    parser = argparse.ArgumentParser(description="Aider/OpenCode Mechanical Constraints Validator")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    all_errors = []
    all_partials = []

    e1, p1 = check_governance_rules_file()
    all_errors.extend(e1)
    all_partials.extend(p1)

    e2, p2 = check_aider_configuration()
    all_errors.extend(e2)
    all_partials.extend(p2)

    e3, p3 = check_hook_integrity()
    all_errors.extend(e3)
    all_partials.extend(p3)

    if all_errors:
        print("FAIL: Aider/OpenCode mechanical constraints validation failed")
        for e in all_errors:
            print(f"  - {e}")
        sys.exit(1)

    if all_partials:
        print("PARTIAL: Aider/OpenCode constraints partially validated")
        for p in all_partials:
            print(f"  PARTIAL: {p}")
        sys.exit(1)

    print("PASS: Aider/OpenCode mechanical constraints validated")
    sys.exit(0)


if __name__ == "__main__":
    main()
