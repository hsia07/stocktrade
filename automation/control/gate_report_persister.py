"""
GOV-INT-002: Evidence Gate Report Persister.

Consumes EvidenceGateOrchestrator's public interface to run the gate pipeline
and writes the standardized gate report JSON to the reports/ directory.

Usage:
    from automation.control.gate_report_persister import persist_gate_report
    report = persist_gate_report(Path("path/to/candidate_dir"))
    # PASS: returns report dict, writes JSON
    # BLOCKED: raises GateBlocked with report attached, still writes JSON
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure repo root is in sys.path for direct script invocation compatibility
_repo_root = str(Path(__file__).resolve().parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from .evidence_gate_orchestrator import EvidenceGateOrchestrator
except ImportError:
    from automation.control.evidence_gate_orchestrator import EvidenceGateOrchestrator

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


class GateBlocked(Exception):
    """Raised when evidence gate verdict is BLOCKED (report is still written)."""

    def __init__(self, report: Dict[str, Any]):
        self.report = report
        blocked_at = report.get("blocked_at_gate", "unknown")
        super().__init__(f"Evidence gate BLOCKED at: {blocked_at}")


def persist_gate_report(
    candidate_dir: Path,
    reports_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run the evidence gate and persist the report to disk.

    Args:
        candidate_dir: Path to the candidate evidence directory.
        reports_dir: Override for the reports output directory (defaults to
                     REPORTS_DIR adjacent to this file).

    Returns:
        The gate report dict.

    Raises:
        NotADirectoryError: If candidate_dir does not exist.
        GateBlocked: If the gate verdict is BLOCKED (report still written).
    """
    candidate_dir = Path(candidate_dir).resolve()
    if not candidate_dir.is_dir():
        raise NotADirectoryError(
            f"Candidate directory not found: {candidate_dir}"
        )

    orch = EvidenceGateOrchestrator()
    report = orch.run_evidence_gate(candidate_dir)

    target_dir = (reports_dir or REPORTS_DIR).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    round_id = report.get("round_id", "UNKNOWN")
    filename = f"{round_id}_gate_report.json"
    filepath = target_dir / filename
    filepath.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if report.get("verdict") == "BLOCKED":
        raise GateBlocked(report)

    return report


def _derive_candidate_dir(repo_root: Path) -> Path:
    """Derive candidate directory from repo root + state file."""
    state_path = repo_root / "automation" / "control" / "state.runtime.json"
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    current_round = state.get("current_round", "UNKNOWN")
    return repo_root / "automation" / "control" / "candidates" / current_round


def main() -> int:
    """CLI entry point: returns 0 on PASS, 1 on BLOCKED, 2 on error."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Evidence Gate Report Persister"
    )
    parser.add_argument(
        "candidate_dir",
        type=str,
        nargs="?",
        default=None,
        help="Path to candidate evidence directory (optional if --repo-root is provided)",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Repo root path. If provided without candidate_dir, "
             "derives candidate path from state.runtime.json",
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        default=None,
        help="Override reports output directory",
    )
    args = parser.parse_args()

    candidate_dir_arg = args.candidate_dir
    if candidate_dir_arg is None:
        if args.repo_root is not None:
            candidate_dir_arg = str(
                _derive_candidate_dir(Path(args.repo_root).resolve())
            )
        else:
            candidate_dir_arg = str(
                _derive_candidate_dir(Path(__file__).resolve().parent.parent.parent)
            )

    try:
        persist_gate_report(
            candidate_dir=Path(candidate_dir_arg),
            reports_dir=Path(args.reports_dir) if args.reports_dir else None,
        )
        return 0
    except GateBlocked as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        print(json.dumps(e.report, indent=2), file=sys.stderr)
        return 1
    except (NotADirectoryError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
