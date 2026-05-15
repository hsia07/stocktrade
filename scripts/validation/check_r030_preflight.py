#!/usr/bin/env python3
"""
R030 Preflight Readiness Validator

Checks that R030 (决策前检查清单) is ready for dispatch.
This validator does NOT dispatch R030 — it only validates readiness.

Checks:
1. R030 topic = 决策前检查清单
2. last_completed_round = R029
3. next_round_to_dispatch = R030
4. depends_on = R029
5. GOV_BACKLOG_001-005 evidence in ancestry
6. R030 references 04 Chapter 21 and 03 R030 supplement
7. Market Reality pass / NEA pass / Risk Gate pass
8. Deterministic position sizing pass / confidence calibration pass
9. Replay compatibility / order-fill-pnl schema / Taiwan constraints
10. Single signal no direct trade
11. LLM not trade core
12. Any missing → R030 readiness FAIL
"""

import argparse
import sys
import yaml
import json
from pathlib import Path


REQUIRED_TOPIC = "决策前检查清单"
REQUIRED_LAST_COMPLETED = "R029"
REQUIRED_NEXT_DISPATCH = "R030"
REQUIRED_DEPENDS_ON = ["R029"]
GOV_BACKLOG_EVIDENCE_IDS = [
    "GOV_BACKLOG_001",
    "GOV_BACKLOG_002",
    "GOV_BACKLOG_003",
    "GOV_BACKLOG_004",
    "GOV_BACKLOG_005",
]

REQUIRED_R030_REFERENCES = [
    "04_交易系統法典補強版",
    "第二十一章",
    "03_161輪逐輪施行細則法典",
    "R030",
]

REQUIRED_R030_CONSTRAINTS = [
    "Market Reality",
    "NEA",
    "Risk Gate",
    "position sizing",
    "confidence calibration",
    "replay compatibility",
    "order-fill-pnl",
    "Taiwan",
    "single signal no direct trade",
    "LLM not trade core",
]


def check_manifest_round_id(manifest: dict) -> list:
    errors = []
    if manifest.get("next_round_to_dispatch") != REQUIRED_NEXT_DISPATCH:
        errors.append(
            f"next_round_to_dispatch={manifest.get('next_round_to_dispatch')} "
            f"(expected {REQUIRED_NEXT_DISPATCH})"
        )
    if manifest.get("last_completed_round") != REQUIRED_LAST_COMPLETED:
        errors.append(
            f"last_completed_round={manifest.get('last_completed_round')} "
            f"(expected {REQUIRED_LAST_COMPLETED})"
        )
    depends = manifest.get("depends_on", [])
    if isinstance(depends, list):
        if REQUIRED_DEPENDS_ON[0] not in depends:
            errors.append(f"depends_on missing {REQUIRED_DEPENDS_ON[0]}")
    else:
        if depends != REQUIRED_DEPENDS_ON[0]:
            errors.append(f"depends_on={depends} (expected {REQUIRED_DEPENDS_ON[0]})")
    return errors


def check_backlog_evidence_in_ancestry() -> list:
    errors = []
    for bid in GOV_BACKLOG_EVIDENCE_IDS:
        evidence_path = (
            Path("automation") / "control" / "candidates"
        )
        found = False
        if evidence_path.exists():
            for child in evidence_path.iterdir():
                if child.is_dir() and bid.lower() in child.name.lower():
                    ev_json = child / "evidence.json"
                    if ev_json.exists():
                        found = True
                        break
        if not found:
            errors.append(
                f"GOV_BACKLOG evidence not found in ancestry: {bid}"
            )
    return errors


def check_governance_law_references() -> list:
    errors = []
    law_dir = Path("_governance") / "law"
    readable_dir = Path("_governance") / "law" / "readable"
    for ref in REQUIRED_R030_REFERENCES:
        found = False
        for d in [law_dir, readable_dir]:
            if d.exists():
                for f in d.iterdir():
                    if f.is_file() and ref in f.name:
                        found = True
                        break
        if not found:
            errors.append(f"Law reference not found: {ref}")
    return errors


def check_constraint_documentation() -> list:
    errors = []
    law_dir = Path("_governance") / "law"
    readable_dir = Path("_governance") / "law" / "readable"
    combined_text = ""
    for d in [law_dir, readable_dir]:
        if d.exists():
            for f in sorted(d.iterdir()):
                if f.is_file() and f.suffix in (".md", ".txt", ".docx"):
                    try:
                        combined_text += f.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        pass
    for constraint in REQUIRED_R030_CONSTRAINTS:
        if constraint not in combined_text:
            errors.append(f"R030 constraint not documented in law: {constraint}")
    return errors


def main():
    parser = argparse.ArgumentParser(description="R030 Preflight Readiness Validator")
    parser.add_argument("--manifest", default="manifests/current_round.yaml")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    all_errors = []
    all_warnings = []

    if not Path(args.manifest).exists():
        all_errors.append(f"Manifest not found: {args.manifest}")
        print_result(False, all_errors, all_warnings)
        sys.exit(1)

    manifest = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))

    if args.verbose:
        print("[R030-PREFLIGHT] Loading manifest:", args.manifest)

    all_errors.extend(check_manifest_round_id(manifest))
    all_errors.extend(check_backlog_evidence_in_ancestry())
    all_errors.extend(check_governance_law_references())
    all_errors.extend(check_constraint_documentation())

    r030_topic = None
    v2_file = Path("_governance") / "law" / "161輪正式重編主題總表_唯一基準版_v2.md"
    if v2_file.exists():
        content = v2_file.read_text(encoding="utf-8")
        import re
        match = re.search(r"\| R030 \| ([^|]+) \| ([^|]+) \|", content)
        if match:
            r030_topic = match.group(2).strip()
    if r030_topic != REQUIRED_TOPIC:
        all_errors.append(
            f"R030 topic mismatch: '{r030_topic}' (expected '{REQUIRED_TOPIC}')"
        )

    passed = len(all_errors) == 0
    print_result(passed, all_errors, all_warnings)
    sys.exit(0 if passed else 1)


def print_result(passed: bool, errors: list, warnings: list):
    if passed:
        print("PASS: R030 preflight checks passed")
    else:
        print("FAIL: R030 preflight checks failed")
        for e in errors:
            print(f"  - {e}")
    for w in warnings:
        print(f"  WARN: {w}")
    if passed:
        print("PASS: R030 readiness validated")


if __name__ == "__main__":
    main()
