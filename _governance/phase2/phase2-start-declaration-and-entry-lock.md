# PHASE 2 START DECLARATION AND ENTRY LOCK

**Round ID:** PHASE2-START-DECLARATION-AND-ENTRY-LOCK  
**Declared At:** 2026-04-23  
**Canonical Base:** `1606a44a9d6429368b42ec8a195a948ed191bac8`  
**Declaration Type:** Governance Entry Lock (Frozen Start)

---

## 1. PHASE 2 SCOPE

Phase 2 encompasses all governance and operational rounds following the formal closure of Phase 1 (R001-R016), including:

- **Governance Rounds:** R017 and beyond, covering continued law maintenance, incident response, mechanical gate hardening, and process evolution.
- **Integration Rounds:** R006-R011 module integration into the main execution chain (`server.py` / `TradingEngine.run_loop()`).
- **Backfill Rounds:** R016-B and any future side-branch backfill rounds for topic correction or historical reconciliation.
- **Runtime Hardening:** Transition from documentation-only locks to runtime-enforced hard stops.
- **Auto-Mode Maturation:** End-to-end testing, lane release preparation, and eventual auto-mode authorization.

**Explicitly Excluded from Phase 2 Scope:**
- Lane release (requires separate authorization)
- Auto-mode release (requires separate authorization)
- STOP_NOW.flag removal (requires separate authorization)
- Master branch promotion (requires separate authorization)

---

## 2. LAUNCH BASIS

Phase 2 is launched under the following verified conditions:

| Condition | Status | Evidence |
|-----------|--------|----------|
| Phase 1 formal closure | ✅ Complete | `phase1-formal-closure-declaration.md` committed |
| Remote sync gap resolved | ✅ Complete | Local and remote both at `1606a44` |
| Mechanical gates active | ✅ Complete | Hook A + Validator B + Template C on local and remote |
| Source-of-truth lock active | ✅ Complete | Old source references blocked, new baseline enforced |
| Double direct-on-canonical incident contained | ✅ Complete | Plan C soft containment + incident documentation |
| Human authorization for Phase 2 entry | ✅ Granted | Explicit user authorization for Phase 2 start declaration |

---

## 3. FROZEN STATUS DECLARATION

**CRITICAL DISTINCTION:**

```
Phase 2 Started != Lane Release Authorized
Phase 2 Started != Auto-Mode Release Authorized
```

Despite entering Phase 2, the following remain **FROZEN** and **NOT AUTHORIZED**:

### 3.1 Lane Status
- `STOP_NOW.flag` **MUST remain present**.
- `run_state` **MUST remain `stopped`**.
- Automation lane **MUST remain frozen**.
- No auto-mode loop **MUST be started** without explicit authorization.

### 3.2 Remaining Lane Release Blockers (LR-001 ~ LR-004)

| Blocker | Description | Impact |
|---------|-------------|--------|
| LR-001 | `runtime/opencode_output.txt` = 15,103 bytes (exceeds threshold) | Prevents clean lane resume |
| LR-002 | Runtime enforcement gap (documentation-only locks, no runtime hard stop) | Prevents trusted auto-mode execution |
| LR-003 | No end-to-end auto-mode testing performed | Prevents operational validation |
| LR-004 | `state.runtime.json` stale (shows R-011, Phase 1) | Prevents automation self-resume |

**Resolution of LR-001 ~ LR-004 requires separate human authorization for a "Lane Release Preparation Round."**

---

## 4. EARLY PHASE 2 PRIORITIES

### Priority 1: R006-R011 Integration into Main Execution Chain
- **Modules:** `HealthMonitor`, `CircuitBreaker`, `FailoverCenter`, `SilenceDetector`, `SilenceRecovery`, `ModeController`, `ModeRecorder`, `PriorityScheduler`, `PriorityMonitor`, `ArtifactManager`
- **Status:** Implemented and tested in standalone form; NOT imported by `server.py`.
- **Action:** Create integration rounds to wire these modules into `TradingEngine.run_loop()` or equivalent main execution path.
- **Authorization Required:** Yes, per-round authorization required.

### Priority 2: R016 Backfill Planning
- **Issue:** Frozen candidate `work/r016-decision-trace` has topic mismatch (health-monitor vs decision-trace).
- **Status:** Deferred. No immediate operational impact.
- **Action:** Plan future side-branch backfill round `R016-B` to correct topic alignment.
- **Authorization Required:** Yes, when backfill round is scheduled.

### Priority 3: Mechanical Gate Residual Hardening
- **Issue:** Template gate C (Section 4B `branch_strategy`) is partially mechanical.
- **Status:** Human-dependent gap remains. Validator does not parse `branch_strategy` content.
- **Action:** Evaluate whether to add parser-based validation for `branch_strategy` field.
- **Risk Level:** Low. Human oversight + source-of-truth lock provides sufficient coverage.

---

## 5. GOVERNANCE ENTRY LOCK RULES

### Rule 5.1 - Phase 2 Round Authorization
Every Phase 2 governance round requires explicit human authorization with:
- `round_id`
- `task_type`
- `scope_boundary` (what is and is not included)

### Rule 5.2 - No Implicit Lane Release
No Phase 2 round may implicitly or explicitly authorize lane release. Lane release requires a dedicated round with:
- Explicit mention of "lane release"
- Resolution plan for LR-001 ~ LR-004
- `lane_release_authorized: true` in round manifest

### Rule 5.3 - No Implicit Auto-Mode Release
No Phase 2 round may implicitly or explicitly authorize auto-mode release. Auto-mode release requires:
- Successful end-to-end testing (LR-003 resolved)
- Runtime hard stops active (LR-002 resolved)
- Clean runtime state (LR-001 and LR-004 resolved)
- Explicit `auto_mode_release_authorized: true` in round manifest

### Rule 5.4 - Side-Branch Workflow Mandatory
All non-merge commits on canonical MUST use the side-branch workflow:
1. Create `work/[round-id]-candidate`
2. Commit all work on candidate branch
3. Merge candidate branch into `work/canonical-mainline-repair-001`
4. Direct commits on canonical are blocked by mechanical Gate A.

---

## 6. AUDIT TRAIL

- **Prior Adjudication:** `PHASE2-READINESS-FINAL-ADJUDICATION` confirmed `phase2_authorization_decision_point_ready = true`.
- **This Declaration:** Formalizes Phase 2 entry while maintaining all frozen locks.
- **Next Expected Action:** Human authorization for either (a) Lane Release Preparation Round, or (b) R006-R011 Integration Round, or (c) continued governance rounds.
