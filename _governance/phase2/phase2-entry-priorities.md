# PHASE 2 ENTRY PRIORITIES

**Document ID:** phase2-entry-priorities  
**Version:** 1.0  
**Canonical Base:** `1606a44a9d6429368b42ec8a195a948ed191bac8`  
**Status:** Active / Frozen Start

---

## PRIORITY 1: R006-R011 INTEGRATION INTO MAIN EXECUTION CHAIN

### 1.1 Objective
Wire all standalone R006-R011 modules into the primary execution path (`server.py` / `TradingEngine.run_loop()`) so that health monitoring, circuit breaking, silence detection, mode governance, priority scheduling, and artifact management become operational in production runtime.

### 1.2 Modules to Integrate

| Module | File Path | Standalone Status | Integration Target |
|--------|-----------|-------------------|-------------------|
| HealthMonitor | `health/monitor.py` | ✅ Implemented & tested | `server.py` startup health checks |
| CircuitBreaker | `circuit/breaker.py` | ✅ Implemented & tested | `server.py` API call wrappers |
| FailoverCenter | *(verify path)* | ✅ Implemented & tested | `server.py` fallback orchestration |
| SilenceDetector | `monitoring/silence/detector.py` | ✅ Implemented & tested | `run_opencode_loop.ps1` / main loop |
| SilenceRecovery | `monitoring/silence/recovery.py` | ✅ Implemented & tested | `run_opencode_loop.ps1` / main loop |
| ModeController | `governance/state_machine/mode_controller.py` | ✅ Implemented & tested | `server.py` mode transitions |
| ModeRecorder | `governance/state_machine/mode_recorder.py` | ✅ Implemented & tested | `server.py` mode audit trail |
| PriorityScheduler | `scheduler/priority/scheduler.py` | ✅ Implemented & tested | `server.py` task queue |
| PriorityMonitor | `scheduler/priority/monitor.py` | ✅ Implemented & tested | `server.py` priority metrics |
| ArtifactManager | `automation/control/artifacts/r011_artifact_management.py` | ✅ Implemented & tested | `server.py` artifact lifecycle |

### 1.3 Integration Approach
- **Round Structure:** Each module integration should be a separate authorized round or grouped logically.
- **Testing Requirement:** Each integration must include a test verifying the module is callable from `server.py` context.
- **Rollback Plan:** Each integration must be reversible without affecting other modules.

### 1.4 Authorization Gate
- **Pre-requisite:** None (can start immediately in Phase 2).
- **Required Authorization:** Per-round explicit human authorization.
- **Forbidden:** No integration round may include lane release or auto-mode release.

---

## PRIORITY 2: R016 BACKFILL PLANNING

### 2.1 Objective
Plan and schedule a future side-branch backfill round (`R016-B`) to correct the topic mismatch in the frozen `work/r016-decision-trace` candidate.

### 2.2 Known Issues
- **Topic Mismatch:** Frozen candidate declares topic "decision-trace" but law table maps R016 to "health-monitor".
- **Impact:** None on current operations. Candidate is frozen and not merged.
- **Correction:** Update topic in candidate or create corrected backfill candidate.

### 2.3 Planning Checklist
- [ ] Determine if `work/r016-decision-trace` should be corrected in-place or replaced.
- [ ] Create `R016-B` candidate branch with corrected topic.
- [ ] Update law table backfill tracking.
- [ ] Obtain explicit authorization for backfill round.

### 2.4 Authorization Gate
- **Pre-requisite:** None.
- **Required Authorization:** Explicit authorization for `R016-B` backfill round.
- **Priority:** Low (deferred).

---

## PRIORITY 3: MECHANICAL GATE RESIDUAL HARDENING

### 3.1 Objective
Close the remaining human-dependent gap in Template Gate C (Section 4B `branch_strategy`).

### 3.2 Current State
- **Template Gate C1:** Section 4B exists and is mandatory. ✅
- **Template Gate C2:** `branch_strategy` field is required in round input. ✅
- **Template Gate C3:** Validator does NOT parse `branch_strategy` content for correctness. ⚠️

### 3.3 Hardening Options

| Option | Description | Effort | Risk |
|--------|-------------|--------|------|
| A. Add parser | Extend `check_branch_workflow.py` to parse template and verify `branch_strategy` is not empty/blocked | Medium | Low |
| B. Schema validation | Add JSON schema validation for round input templates | High | Medium |
| C. Human oversight | Maintain current state; rely on human review + source-of-truth lock | None | Low (acceptable) |

### 3.4 Recommendation
**Option C (maintain current state)** is acceptable for Phase 2. The combination of:
- Hook A blocking direct canonical commits
- Validator B blocking old sources and enforcing source-of-truth
- Human oversight for template completeness

provides sufficient fail-closed coverage. Option A or B may be pursued in future governance rounds if risk appetite changes.

### 3.5 Authorization Gate
- **Pre-requisite:** None.
- **Required Authorization:** If pursuing Option A or B, explicit authorization for gate hardening round.
- **Priority:** Low.

---

## PRIORITY 4: LANE RELEASE PREPARATION (FUTURE)

### 4.1 Objective
Prepare for eventual lane release by resolving LR-001 ~ LR-004.

### 4.2 Resolution Map

| Blocker | Resolution Action | Estimated Round Type |
|---------|-------------------|----------------------|
| LR-001 | Clear `runtime/opencode_output.txt` or archive it | Housekeeping round |
| LR-002 | Implement runtime hard stop (e.g., process-level guard) | Engineering round |
| LR-003 | Execute end-to-end auto-mode test | Testing round |
| LR-004 | Update `state.runtime.json` to reflect Phase 2, R017+ | State update round |

### 4.3 Authorization Gate
- **Pre-requisite:** Phase 2 early priorities may be partially completed.
- **Required Authorization:** Dedicated "Lane Release Preparation Round" with explicit `lane_release_authorized: true`.
- **Forbidden:** Lane release preparation may NOT be bundled with other Phase 2 work without explicit authorization.

---

## DOCUMENT CONTROL

- **Created By:** PHASE2-START-DECLARATION-AND-ENTRY-LOCK
- **Next Review:** Before first Phase 2 integration round
- **Change History:**
  - v1.0 (2026-04-23): Initial creation at Phase 2 frozen start.
