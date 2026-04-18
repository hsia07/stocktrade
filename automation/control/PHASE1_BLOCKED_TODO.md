Phase 1 Blocked Todo
====================

Overview
- R-007: absorbed/content-equivalent historical work (baseline)
- R-008: absorbed/content-equivalent historical work (baseline)
- R-009: blocked; local merge performed, acceptance blocked by environment/evidence insufficiency
- Phase 1 remains not closed; current blocker = R-009

Blockers (three categories)
- History reachability blocker: baseline history range 941cd18bd25e55002fade912d3858a805034b9b8..0493cf8d95cd8777d8ce4d442f35d3b65258dd4f not yet reachable in this environment
- Candidate evidence integrity blocker: unable to conclusively verify candidate diff/report integrity in current env
- Validation environment blocker: Python/pytest tooling not reliably available here

Unblock prerequisites (precise requirements)
- Baseline history reachability: ability to fetch/unshallow baseline and enumerate all commits in the range 941cd18bd25e55002fade912d3858a805034b9b8..0493cf8d95cd8777d8ce4d442f35d3b65258dd4f
- Candidate evidence integrity: possess a mechanism to compare baseline vs source vs merge post-merge for the 6 R-009 files; determine integrity outcome (true/false)
- Validation environment readiness: confirm Python interpreter and either pytest or minimal static validation tooling; provide exact blockers if not

Minimal runbook commands for unblock (to be executed in proper environment)
- Baseline reachability and fetch steps:
  - git fetch --unshallow origin work/canonical-mainline-repair-001
  - git fetch --tags --prune origin
  - git log --oneline 941cd18bd25e55002fade912d3858a805034b9b8..0493cf8d95cd8777d8ce4d442f35d3b65258dd4f
- Baseline gap enumeration (if reachable):
  - git log --oneline 941cd18bd25e55002fade912d3858a805034b9b8..0493cf8d95cd8777d8ce4d442f35d3b65258dd4f
- Candidate diff/report integrity checks:
  - git diff 941cd18bd25e55002fade912d3858a805034b9b8...0493cf8d95cd8777d8ce4d442f35d3b65258dd4f -- automation/control/candidates/R9-COMMAND-PRIORITY-001/candidate.diff
  - git diff 941cd18bd25e55002fade912d3858a805034b9b8...0493cf8d95cd8777d8ce4d442f35d3b65258dd4f -- automation/control/candidates/R9-COMMAND-PRIORITY-001/report.json
- Python static validation (if Python available):
  - python -m py_compile scheduler/priority/monitor.py scheduler/priority/scheduler.py tests/test_r009_command_priority.py
- PyTest availability check:
  - pytest --version
- If pytest is available, run: pytest -q tests/test_r009_command_priority.py

Acceptance criteria for unblock success
- candidate_evidence_integrity_ok must be non-null in the future environment
- baseline gap must be enumerable in the proper environment
- at least one real static validation result must be produced

Notes
- Do not push; this is strictly a blocker unblock plan for governance to authorize re-entry into acceptance workflow in a proper environment.
