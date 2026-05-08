"""
BLOCKER_C: NEA round-scoped auto-injection registry (v0.1).

Provides round-scoped patch/injection mapping for bounded auto construction.
Each round in the sequence has its own mandatory sections defined here.
Only the target round's sections are injected — never roadmap_only,
never cross-round contamination.

Injection is machine-checkable: verify_injection() confirms scope,
roadmap exclusion, and no contamination.

NEA architecture:
  v0.1 (current): round-scoped injection, no global injection, mandatory
  v0.2/v1.0 (roadmap): defined as roadmap_only, NEVER injected in v0.1
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("round_injection_registry")

# Active round injection map (v0.1, NEA round-scoped)
# Each entry is scoped to exactly one round. No global injection.
ROUND_INJECTION_MAP: Dict[str, Dict[str, Any]] = {
    "BLOCKER_C": {
        "mandatory_sections": [
            "NEA round-scoped injection registry established",
            "patch/round injection mapping: round_id → mandatory_sections",
            "machine-checkable injection validation: scope, roadmap, contamination",
            "no global injection: only target round receives its sections",
            "no roadmap_only injection: future-round sections never injected early",
            "inject_into_scaffold(): enriches task.txt with round-specific requirements",
            "inject_into_scaffold(): enriches evidence.json with round-scoped metadata",
        ],
        "roadmap_only": False,
    },
    "BLOCKER_D": {
        "mandatory_sections": [
            "pre-push bash hook → PowerShell rewrite for unattended auto-advance",
            "pre-push check: round evidence, law compliance, merge authorization",
            "no --no-verify bypass allowed in auto-advance mode",
        ],
        "roadmap_only": False,
    },
    "AUTO_ADVANCE_OPERATIONAL": {
        "mandatory_sections": [
            "bounded auto construction final certification",
            "full auto-advance mode activation verification",
            "all 8 blockers (G, FIX, F, E, I, H, C, D) formally closed",
        ],
        "roadmap_only": False,
    },
}

# Roadmap-only rounds (v0.2/v1.0) — NEVER injected in bounded auto construction
ROADMAP_ONLY_INJECTIONS: Dict[str, Dict[str, Any]] = {
    "AUTO_ADVANCE_V0_2": {
        "mandatory_sections": [
            "multi-round parallel injection support",
            "telemetry-driven dispatch optimization",
            "adaptive round sequencing",
        ],
        "roadmap_only": True,
    },
    "AUTO_ADVANCE_V1_0": {
        "mandatory_sections": [
            "autonomous merge governance with ML validation",
            "full lifecycle automation without human signoff",
            "cross-repository dispatch coordination",
        ],
        "roadmap_only": True,
    },
}


def get_round_injection(round_id: str) -> dict | None:
    """
    Get mandatory injection content for a specific round.

    Returns dict with mandatory_sections list or None if round is
    roadmap_only or unknown. Never injects roadmap_only content.
    """
    injection = ROUND_INJECTION_MAP.get(round_id.upper().strip())
    if injection:
        return dict(injection)
    return None


def is_roadmap_only(round_id: str) -> bool:
    """Check if a round is roadmap_only (v0.2/v1.0, never injected in v0.1)."""
    return round_id.upper().strip() in ROADMAP_ONLY_INJECTIONS


def get_all_active_round_ids() -> list[str]:
    """Return all non-roadmap round IDs in the registry."""
    return list(ROUND_INJECTION_MAP.keys())


def inject_into_scaffold(scaffold_dir: Path, round_id: str) -> dict:
    """
    Enrich a scaffold directory with round-specific mandatory sections.

    Only injects for the target round_id. Never injects roadmap_only.
    Never injects sections from other rounds.

    Args:
        scaffold_dir: path to candidate scaffold directory
        round_id: target round ID (case-insensitive)

    Returns:
        dict with injection outcome including safety flags.
    """
    round_upper = round_id.upper().strip()

    if is_roadmap_only(round_upper):
        return {
            "round_id": round_id,
            "injection_applied": False,
            "injected_sections": [],
            "roadmap_only_skipped": True,
            "cross_round_injection": False,
            "merge_executed": False,
            "push_executed": False,
            "promote_executed": False,
            "pr_created": False,
        }

    injection = get_round_injection(round_upper)
    if not injection:
        return {
            "round_id": round_id,
            "injection_applied": False,
            "injected_sections": [],
            "reason": "no_injection_defined_for_round",
            "cross_round_injection": False,
            "merge_executed": False,
            "push_executed": False,
            "promote_executed": False,
            "pr_created": False,
        }

    sections = injection.get("mandatory_sections", [])
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Enrich task.txt
    task_path = scaffold_dir / "task.txt"
    header = f"Injected mandatory sections ({timestamp}):\n"
    section_lines = "\n".join(f"  - {s}" for s in sections)
    if task_path.exists():
        existing = task_path.read_text(encoding="utf-8")
        enriched = existing.rstrip() + "\n\n" + header + section_lines + "\n"
        task_path.write_text(enriched, encoding="utf-8")
    else:
        content = f"=== {round_upper} ===\n\n{header}{section_lines}\n"
        task_path.write_text(content, encoding="utf-8")

    # Enrich evidence.json
    evidence_path = scaffold_dir / "evidence.json"
    evidence = {}
    if evidence_path.exists():
        try:
            with open(evidence_path, "r", encoding="utf-8") as f:
                evidence = json.load(f)
        except Exception:
            evidence = {}
    evidence["round_id"] = round_upper
    evidence["injection_applied"] = True
    evidence["injected_at"] = timestamp
    evidence["injected_sections"] = sections
    evidence["cross_round_injection"] = False
    evidence["roadmap_only_injected"] = False
    evidence["merge_blocked"] = True
    evidence["push_blocked"] = True
    evidence["promote_blocked"] = True
    evidence["merge_executed"] = False
    evidence["push_executed"] = False
    evidence["promote_executed"] = False
    evidence["pr_created"] = False
    evidence_path.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return {
        "round_id": round_upper,
        "injection_applied": True,
        "injected_sections": sections,
        "roadmap_only_skipped": False,
        "cross_round_injection": False,
        "merge_executed": False,
        "push_executed": False,
        "promote_executed": False,
        "pr_created": False,
    }


def verify_injection(scaffold_dir: Path, round_id: str) -> tuple[bool, list[str]]:
    """
    Machine-checkable verification of round-scoped injection.

    Checks:
    1. evidence.json exists and is valid JSON
    2. injection_applied is True
    3. round_id matches expected
    4. No roadmap_only injection (roadmap_only_injected must be False)
    5. No cross-round contamination (cross_round_injection must be False)
    6. All merge/push/promote/pr flags are False

    Returns (valid, issues_found).
    """
    issues = []
    evidence_path = scaffold_dir / "evidence.json"
    if not evidence_path.exists():
        return False, ["scaffold_missing:evidence.json"]

    try:
        with open(evidence_path, "r", encoding="utf-8") as f:
            evidence = json.load(f)
    except Exception as e:
        return False, [f"evidence_parse_error:{e}"]

    if not evidence.get("injection_applied"):
        issues.append("injection_not_applied")

    evidence_round = evidence.get("round_id", "")
    if evidence_round.upper().strip() != round_id.upper().strip():
        issues.append(f"round_id_mismatch:expected={round_id},got={evidence_round}")

    if evidence.get("roadmap_only_injected"):
        issues.append("roadmap_only_injected:forbidden")

    if evidence.get("cross_round_injection"):
        issues.append("cross_round_contamination_detected")

    for flag in ["merge_executed", "push_executed", "promote_executed", "pr_created"]:
        if evidence.get(flag) is not False:
            issues.append(f"{flag}_not_false")

    return len(issues) == 0, issues


def verify_no_cross_round_contamination(
    scaffold_dir: Path, round_id: str
) -> tuple[bool, list[str]]:
    """
    Verify that no sections from other rounds exist in this scaffold's evidence.

    Checks injected_sections against all other rounds' mandatory_sections
    (both active and roadmap_only). Any overlap = contamination.
    """
    issues = []
    evidence_path = scaffold_dir / "evidence.json"
    if not evidence_path.exists():
        return False, ["scaffold_missing:evidence.json"]

    try:
        with open(evidence_path, "r", encoding="utf-8") as f:
            evidence = json.load(f)
    except Exception as e:
        return False, [f"evidence_parse_error:{e}"]

    injected = evidence.get("injected_sections", [])
    if not injected:
        return True, []

    round_upper = round_id.upper().strip()

    for other_round, other_injection in ROUND_INJECTION_MAP.items():
        if other_round == round_upper:
            continue
        for section in injected:
            if section in other_injection.get("mandatory_sections", []):
                issues.append(
                    f"cross_contamination:section_from_{other_round}_in_{round_upper}"
                )

    for other_round, other_injection in ROADMAP_ONLY_INJECTIONS.items():
        for section in injected:
            if section in other_injection.get("mandatory_sections", []):
                issues.append(
                    f"cross_contamination:section_from_roadmap_{other_round}_in_{round_upper}"
                )

    return len(issues) == 0, issues
