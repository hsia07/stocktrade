R-009 Unblock Runbook
====================================

Overview
- This runbook documents the concrete steps required to unblock R-009 in a proper environment, and how to re-enter the R-009 acceptance workflow without altering core code or pushing in this phase.

Current status (as of this run)
- canonical mainline baseline: work/canonical-mainline-repair-001
- R-007: absorbed/content-equivalent historical work branch (closed in baseline)
- R-008: absorbed/content-equivalent historical work branch (closed in baseline)
- R-009: blocked; local merge performed; acceptance blocked by environment/evidence insufficiency
- Phase 1: not closed; blocker = R-009

Blocker categories (three):
- History reachability blocker
- Candidate evidence integrity blocker
- Validation environment blocker

In the proper environment, the first unblock actions should cover:
- Baseline history reachability: ensure full git history reachability for baseline 941cd18...0493cf8
- Candidate evidence integrity: compare baseline vs source vs merged post-merge for the six R-009 files and determine integrity result
- Static validation: verify python/pytest availability and run a minimal validation (py_compile or import checks)

Unblock prerequisites (precise phrasing):
- Baseline reachability: fetch --unshallow origin work/canonical-mainline-repair-001; fetch --tags --prune origin; then enumerate commits between 941cd18bd25e55002fade912d3858a805034b9b8 and 0493cf8d95cd8777d8ce4d442f35d3b65258dd4f
- Integrity check readiness: prepare per-file differential analysis for
  automation/control/candidates/R9-COMMAND-PRIORITY-001/candidate.diff and
  automation/control/candidates/R9-COMMAND-PRIORITY-001/report.json
- Validation readiness: confirm Python/pytest tooling; if unavailable, document blockers with exact messages

First runbook commands (in proper environment):
- Baseline reachability
  git fetch --unshallow origin work/canonical-mainline-repair-001
  git fetch --tags --prune origin
  git log --oneline 941cd18bd25e55002fade912d3858a805034b9b8..0493cf8d95cd8777d8ce4d442f35d3b65258dd4f --no-merges
- Baseline gap enumeration (exact set of commits between)
  git log --oneline 941cd18bd25e55002fade912d3858a805034b9b8..0493cf8d95cd8777d8ce4d442f35d3b65258dd4f
- Integrity checks for candidate diff/report.json
  git diff 941cd18bd25e55002fade912d3858a805034b9b8...0493cf8d95cd8777d8ce4d442f35d3b65258dd4f -- automation/control/candidates/R9-COMMAND-PRIORITY-001/candidate.diff
  git diff 941cd18bd25e55002fade912d3858a805034b9b8...0493cf8d95cd8777d8ce4d442f35d3b65258dd4f -- automation/control/candidates/R9-COMMAND-PRIORITY-001/report.json

- Minimal static validation (if Python available)
  python -m py_compile scheduler/priority/monitor.py scheduler/priority/scheduler.py tests/test_r009_command_priority.py
  pytest --version || echo "pytest not available"

Unblock validation success criteria (when environment is ready):
- candidate_evidence_integrity_ok is non-null
- baseline gap is enumerable
- at least one minimal validation command yields a result

Restart policy after unblock
- Do not push until governance signs off; R-009 blocked remains in effect until unblock criteria are satisfied

Notes
- This runbook is a blueprint for future environment provisioning and is not a substitute for actual governance sign-off.
