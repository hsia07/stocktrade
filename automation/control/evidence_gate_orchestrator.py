"""
GOV-INFRA-006: Evidence Gate Orchestrator.

Orchestrates 3 gate stages (completeness -> schema -> integrity) with
fail-fast short-circuit, invoking only existing evidence_checker.py methods,
and outputs a standardized machine-readable gate report JSON.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from automation.control.evidence_checker import EvidenceChecker

logger = logging.getLogger("evidence_gate_orchestrator")

GATE_COMPLETENESS = "completeness"
GATE_SCHEMA = "schema"
GATE_INTEGRITY = "integrity"

GATE_ROUND_MAPPING: Dict[str, List[str]] = {
    GATE_COMPLETENESS: ["GOV-INFRA-002", "GOV-INFRA-003"],
    GATE_SCHEMA: ["GOV-INFRA-004"],
    GATE_INTEGRITY: ["GOV-INFRA-005"],
}

GATE_EXECUTION_ORDER: List[str] = [
    GATE_COMPLETENESS,
    GATE_SCHEMA,
    GATE_INTEGRITY,
]


def _run_single_gate(
    checker: EvidenceChecker,
    gate: str,
    candidate_dir: Path,
) -> Dict[str, Any]:
    gate_methods = {
        GATE_COMPLETENESS: lambda: checker.check_completeness(candidate_dir),
        GATE_SCHEMA: lambda: checker.validate_evidence_content_schema(candidate_dir),
        GATE_INTEGRITY: lambda: checker.validate_evidence_cross_file_integrity(candidate_dir),
    }
    fn = gate_methods.get(gate)
    if fn is None:
        raise ValueError(f"Unknown gate: {gate}")

    passed, errors = fn()
    return {
        "gate": gate,
        "gov_infra_rounds": GATE_ROUND_MAPPING.get(gate, []),
        "status": "passed" if passed else "failed",
        "errors": errors if errors else [],
        "error_codes": [_extract_error_code(e) for e in errors] if errors else [],
    }


def _extract_error_code(error_str: str) -> str:
    return error_str.split(":")[0] if ":" in error_str else error_str


def _build_gate_report(
    candidate_dir: Path,
    verdict: str,
    blocked_at_gate: Optional[str],
    per_check_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "report_type": "evidence_gate_report",
        "round_id": "GOV-INFRA-006",
        "candidate_dir": str(candidate_dir),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "blocked_at_gate": blocked_at_gate,
        "per_check_results": per_check_results,
    }


class EvidenceGateOrchestrator:
    def __init__(self, repo_root: Optional[Path] = None):
        self.checker = EvidenceChecker(repo_root=repo_root)

    def run_evidence_gate(self, candidate_dir: Path) -> Dict[str, Any]:
        candidate_dir = Path(candidate_dir).resolve()
        if not candidate_dir.is_dir():
            raise NotADirectoryError(f"Candidate directory not found: {candidate_dir}")

        per_check_results: List[Dict[str, Any]] = []
        verdict = "PASS"
        blocked_at: Optional[str] = None

        for gate in GATE_EXECUTION_ORDER:
            result = _run_single_gate(self.checker, gate, candidate_dir)
            per_check_results.append(result)

            if result["status"] == "failed":
                verdict = "BLOCKED"
                blocked_at = gate
                remaining = GATE_EXECUTION_ORDER[GATE_EXECUTION_ORDER.index(gate) + 1:]
                for skipped_gate in remaining:
                    per_check_results.append({
                        "gate": skipped_gate,
                        "gov_infra_rounds": GATE_ROUND_MAPPING.get(skipped_gate, []),
                        "status": "skipped",
                        "errors": [],
                        "error_codes": [],
                    })
                break

        report = _build_gate_report(candidate_dir, verdict, blocked_at, per_check_results)
        return report
