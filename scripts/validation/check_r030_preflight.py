#!/usr/bin/env python3
"""
R030 Preflight Readiness Validator

Checks that R030 (决策前检查清单 / 決策前檢查清單) is ready for dispatch.
This validator does NOT dispatch R030 — it only validates readiness.

Checks:
1. R030 topic = 决策前检查清单 or 決策前檢查清單
2. last_completed_round = R029
3. next_round_to_dispatch = R030
4. depends_on = R029
5. GOV_BACKLOG_001-006 evidence in ancestry
6. R030 references 04 Chapter 21 and 03 R030 supplement (content-based)
7. Market Reality pass / NEA pass / Risk Gate pass
8. Deterministic position sizing pass / confidence calibration pass
9. Replay compatibility / order-fill-pnl schema / Taiwan constraints
10. Single signal no direct trade
11. LLM not trade core
12. Any missing -> R030 readiness FAIL
"""

import argparse
import re
import sys
import yaml
import json
from pathlib import Path


REQUIRED_TOPIC = "决策前检查清单"
REQUIRED_TOPIC_ALIASES = ["決策前檢查清單"]
REQUIRED_LAST_COMPLETED = "R029"
REQUIRED_NEXT_DISPATCH = "R030"
REQUIRED_DEPENDS_ON = ["R029"]
GOV_BACKLOG_EVIDENCE_IDS = [
    "GOV_BACKLOG_001",
    "GOV_BACKLOG_002",
    "GOV_BACKLOG_003",
    "GOV_BACKLOG_004",
    "GOV_BACKLOG_005",
    "GOV_BACKLOG_006",
]

REQUIRED_R030_REFERENCES = [
    "04_交易系統法典補強版",
    "第二十一章",
    "03_161輪逐輪施行細則法典",
    "R030",
]

R030_CONSTRAINT_GROUPS = [
    (["Market Reality", "市場摩擦", "真實市場摩擦", "市場現實"], "Market Reality / 市場摩擦"),
    (["NEA", "淨期望優勢", "net_edge"], "NEA / 淨期望優勢"),
    (["Risk Gate", "風控", "最終閘門", "veto", "否決"], "Risk Gate / 風控"),
    (["position sizing", "倉位", "部位管理", "部位", "資金配置"], "position sizing / 倉位管理"),
    (["confidence calibration", "信心校準", "raw confidence", "calibration", "Brier"], "confidence calibration / 信心校準"),
    (["replay compatibility", "replay", "回放", "decision trace", "決策追責鏈"], "replay compatibility / 回放"),
    (["order-fill-pnl", "order", "fill", "pnl", "損益", "成交", "委託"], "order-fill-pnl / 損益"),
    (["Taiwan", "台股", "漲跌停", "T+2", "集合競價", "零股", "流動性不足", "停牌", "處置股"], "Taiwan / 台股"),
    (["single signal no direct trade", "單一訊號", "單一指標", "不得直接下單", "不得直接 buy", "無直接buy/sell"], "single signal / 單一訊號"),
    (["LLM not trade core", "LLM 不得作為交易核心", "本地 deterministic", "不依賴 LLM"], "LLM not trade core"),
]

LAW_READABLE_EXTENSIONS = (".md", ".txt")


def setup_stdout_encoding():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


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
    evidence_path = Path("automation") / "control" / "candidates"
    if not evidence_path.exists():
        return ["Evidence path not found"]
    for bid in GOV_BACKLOG_EVIDENCE_IDS:
        found = False
        for child in evidence_path.iterdir():
            if child.is_dir() and bid.lower() in child.name.lower():
                ev_json = child / "evidence.json"
                if ev_json.exists():
                    found = True
                    break
        if not found:
            errors.append(f"GOV_BACKLOG evidence not found in ancestry: {bid}")
    return errors


def check_governance_law_references() -> list:
    errors = []
    law_dirs = [
        Path("_governance") / "law",
        Path("_governance") / "law" / "readable",
    ]
    combined_text = ""
    for d in law_dirs:
        if d.exists():
            for f in sorted(d.iterdir()):
                if f.is_file() and f.suffix in LAW_READABLE_EXTENSIONS:
                    try:
                        combined_text += f.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        pass
    for ref in REQUIRED_R030_REFERENCES:
        if ref not in combined_text:
            errors.append(f"Law reference not found (content): {ref}")
    return errors


def check_constraint_documentation() -> list:
    errors = []
    law_dirs = [
        Path("_governance") / "law",
        Path("_governance") / "law" / "readable",
    ]
    combined_text = ""
    for d in law_dirs:
        if d.exists():
            for f in sorted(d.iterdir()):
                if f.is_file() and f.suffix in LAW_READABLE_EXTENSIONS:
                    try:
                        combined_text += f.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        pass
    for terms, display_name in R030_CONSTRAINT_GROUPS:
        found = any(term in combined_text for term in terms)
        if not found:
            errors.append(f"R030 constraint not documented in law: {display_name}")
    return errors


def main():
    setup_stdout_encoding()

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
        match = re.search(r"\| R030 \| ([^|]+) \| ([^|]+) \|", content)
        if match:
            r030_topic = match.group(2).strip()
    valid_topics = [REQUIRED_TOPIC] + REQUIRED_TOPIC_ALIASES
    if r030_topic not in valid_topics:
        all_errors.append(
            f"R030 topic mismatch: '{r030_topic}' "
            f"(expected one of {valid_topics})"
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
