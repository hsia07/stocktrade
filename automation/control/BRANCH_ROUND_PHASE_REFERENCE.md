# Branch / Round / Phase / Runtime Legal Status Reference

## Canonical Mainline Baseline

- **Current Canonical Mainline**: `work/canonical-mainline-repair-001`
- **Legal Status**: VERIFIED - R-006 theme (Health Check / Circuit Breaker / Degradation Center) completed
- **State Sync**: Completed with zero drift
- **Push Authorization**: NOT AUTHORIZED - requires explicit human signoff

## Branch Legal Status Table

| Branch | Round Reference | Legal Status | Phase Role | Note |
|--------|-----------------|--------------|------------|------|
| **work/canonical-mainline-repair-001** | R-006 | **CANONICAL MAINLINE BASELINE** | Phase 1 | Currently verified, ready for consideration |
| **work/phase1-consolidation** | R-006 (Phase 1 base point) | **WORK** (active work branch) | Phase 1 | RENAMED from work/r006-governance - now correctly named |
| work/r007-silence-protection | R-007 | ABSORBED / CONTENT-EQUIVALENT HISTORICAL WORK BRANCH | Phase 1 | Content absorbed into canonical mainline baseline; branch remains as historical reference |
| work/r008-state-machine-governance | R-008 | WORK (not merged) | Phase 1 | R-008 complete but not merged back |
| work/r009-command-priority | R-009 | WORK (not merged) | Phase 1 | R-009 complete but not merged back |
| **candidates/multi-round-attempt-001** | R-006~R-015 | CANDIDATE STALLED | Phase 1 | RENAMED from candidates/R-015 - now correctly named |
| candidates/R-010 | R-010 | INVALIDATED | Phase 1 |废止 |
| candidates/R-011 | R-011 | INVALIDATED | Phase 1 |废止 |
| candidates/R-012 | R-012 | INVALIDATED | Phase 1 |废止 |
| candidates/R-013 | R-013 | INVALIDATED | Phase 1 |废止 |
| candidates/R-014 | R-014 | INVALIDATED | Phase 1 |废止 |
| candidates/R-006 | R-006 | CANDIDATE | Phase 1 | Historical candidate |
| review/R6-HEALTH-CIRCUIT-FAILOVER-001 | R-006 | REVIEW COMPLETED | Phase 1 | Already merged to work |
| review/R7-SILENCE-PROTECTION-001 | R-007 | REVIEW COMPLETED | Phase 1 | Already merged to work |
| review/R8-STATE-MACHINE-001 | R-008 | REVIEW COMPLETED | Phase 1 | Already merged to work |
| review/R9-COMMAND-PRIORITY-001 | R-009 | REVIEW COMPLETED | Phase 1 | Already merged to work |
| master | N/A | PROTECTED | N/A | No direct push allowed |

## Five Concepts Clearly Separated

### A. round_id (輪次)
The specific round being executed or completed.
- Example: R-006, R-007, R-008, R-009

### B. branch (Git branch)
The Git branch where work happens.
- Example: work/canonical-mainline-repair-001, work/r007-silence-protection

### C. phase (Phase 分組)
The Phase grouping for governance.
- Phase 1 = R-001 ~ R-015 (穩定性與基礎建設)
- Phase 2 = R-016 ~ R-045A (交易鏈追責與執行)
- Phase 3 = R-046 ~ R-128 (成熟化與 shadow 準備)
- Phase 4 = R-129 ~ R-161 (多帳戶與營運化)

### D. runtime snapshot
The current execution state in state.runtime.json.

### E. Legal Status
- CANONICAL MAINLINE BASELINE: Verified baseline, ready for consideration
- WORK: Work in progress, not merged
- CANDIDATE: Candidate preparation
- CANDIDATE STALLED: Attempt that stopped
- INVALIDATED: Formally invalidated
- REVIEW COMPLETED: Passed review, merged back
- PROTECTED: Cannot directly push

## Misleading Names Detected

| Name | Why Misleading | Recommendation |
|------|---------------|-----------------|
| work/phase1-consolidation | Contains R-006 but is Phase 1 base point, not R-006 completion | RENAMED to `work/phase1-consolidation` (EXECUTED) |
| candidates/multi-round-attempt-001 | Named R-015 but is actually multi-round attempt (R-006~R-015) | RENAMED to `candidates/multi-round-attempt-001` (EXECUTED) |
| current_phase in state | Was showing R-006 instead of Phase 1 | FIXED - now shows "Phase 1" |

## Current Runtime State (from state.runtime.json)

- **round_id**: R-006
- **branch**: work/canonical-mainline-repair-001
- **current_phase**: Phase 1
- **run_state**: stopped
- **last_action**: r006_purified_validation_completed

## Phase Definition

| Phase | Round Range | Description |
|-------|------------|-------------|
| Phase 1 | R-001 ~ R-015 | 穩定性與基礎建設 |
| Phase 2 | R-016 ~ R-045A | 交易鏈追責與執行 |
| Phase 3 | R-046 ~ R-128 | 成熟化與 shadow 準備 |
| Phase 4 | R-129 ~ R-161 | 多帳戶與營運化 |

## R-006 Official Theme

According to 03_161輪逐輪施行細則法典_整合法條增補版:
- **Theme**: 健康檢查 / 熔斷 / 降級中心
- **Source of Truth**: 03 (not external 05 supplement)
- **Verification**: Passed with 12/12 tests

## Push Authorization Status

- **NOT AUTHORIZED**: Push requires explicit human signoff
- This document does NOT constitute push authorization

---

*Last Updated: 2026-04-19*
*Status: Reference document, not governance hard rule*
