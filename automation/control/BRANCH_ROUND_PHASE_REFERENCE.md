# Branch / Round / Phase / Runtime Legal Status Reference

## Canonical Mainline Baseline

- **Current Canonical Mainline**: `work/canonical-mainline-repair-001`
- **Legal Status**: PHASE 1 FORMALLY CLOSED — R001-R016 all resolved (15 merged, 1 replaced by R008)
- **Phase 2 Status**: HYGIENE ALIGNED — R017 entry pending explicit human authorization
- **Lane Release**: COMPLETED — STOP_NOW.flag removed

## Branch Legal Status Table

| Branch | Round Reference | Legal Status | Phase Role | Note |
|--------|-----------------|--------------|------------|------|
| **work/canonical-mainline-repair-001** | R017 | **CANONICAL MAINLINE BASELINE** | Phase 2 | Phase 2 entry hygiene aligned. R017 not yet authorized to start. |
| **work/phase1-consolidation** | R006 (Phase 1 base point) | ABSORBED | Phase 1 | Historical reference only; Phase 1 complete |
| work/r007-silence-protection | R007 | ABSORBED / CONTENT-EQUIVALENT HISTORICAL WORK BRANCH | Phase 1 | Content absorbed into canonical mainline baseline |
| work/r008-state-machine-governance | R008 | ABSORBED / CONTENT-EQUIVALENT HISTORICAL WORK BRANCH | Phase 1 | R008 replaced R010; mode governance covers core/non-core isolation |
| work/r009-command-priority | R009 | MERGED+REMOTE | Phase 1 | EVIDENCE RERULED / REACCEPTANCE READY; functional content in canonical chain |
| **work/R016-MINIMAL-DOCUMENTATION-BACKFILL-candidate** | R016 | MERGED+REMOTE | Phase 1 | Minimal documentation backfill; schema_version frozen; API schema documented |
| work/r016-decision-trace | R016 | INVALIDATED | Phase 1 | WRONG TOPIC — "Decision source traceability" vs law "欄位命名/API schema/資料契約固定"; fully excluded |
| **candidates/multi-round-attempt-001** | R006-R015 | CANDIDATE STALLED | Phase 1 | Historical reference only |
| candidates/R-011 | R011 | INVALIDATED | Phase 1 |废止 |
| candidates/R-012 | R012 | INVALIDATED | Phase 1 |废止 |
| candidates/R-013 | R013 | INVALIDATED | Phase 1 |废止 |
| candidates/R-014 | R014 | INVALIDATED | Phase 1 |废止 |
| candidates/R-006 | R006 | CANDIDATE | Phase 1 | Historical candidate |
| review/R6-HEALTH-CIRCUIT-FAILOVER-001 | R006 | REVIEW COMPLETED | Phase 1 | Already merged |
| review/R7-SILENCE-PROTECTION-001 | R007 | REVIEW COMPLETED | Phase 1 | Already merged |
| review/R8-STATE-MACHINE-001 | R008 | REVIEW COMPLETED | Phase 1 | Already merged |
| review/R9-COMMAND-PRIORITY-001 | R009 | REVIEW COMPLETED | Phase 1 | Already merged |
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
| work/r007-silence-protection | Absorbed into canonical baseline; not a separate alias | ABSORBED (EXECUTED) |
| current_phase in state | Was showing R-006 instead of Phase 1 | FIXED - now shows "Phase 1" |

## Phase 1 Status (FORMALLY CLOSED)

- Phase 1 Status: **FORMALLY CLOSED** — Phase 1 formal closure signed off
- R001-R005: Absorbed into baseline
- R006: MERGED+REMOTE (HealthMonitor/CircuitBreaker/DegradationCenter)
- R007: MERGED+REMOTE (SilenceDetector/SilenceRecovery)
- R008: MERGED+REMOTE (ModeController/ModeRecorder; also replaced R010)
- R009: MERGED+REMOTE (Execution model; advisory overlay)
- R010: REPLACED by R008
- R011: MERGED+REMOTE (ArtifactManager/caching/EMAs)
- R012: MERGED+REMOTE (DecisionLatencyBudget/DataPathSeparator)
- R013: Absorbed
- R014: MERGED+REMOTE (ObservableEvent schema)
- R015: MERGED+REMOTE (MultiLayerCache)
- R016: MERGED+REMOTE (schema_version/API schema/25 contract tests)
- R016 old wrong topic (DecisionTracer): EXCLUDED

## Phase 2 Status

- Phase 2 Status: HYGIENE ALIGNED — lane released
- R017: awaiting_authorization (topic: 秘密與金鑰管理)
- Phase 2 entry: NOT YET AUTHORIZED
- Auto-mode: NOT YET AUTHORIZED

## R-009 Reruling Summary

- R009 functional content: MERGED+REMOTE at commits 48c480b/6a22130
- Evidence gap: KNOWN GOVERNANCE DEBT (old commit hash in evidence files predating 161-round normalization)
- Functional impact: NONE (code is in canonical chain)
- R009 manifest gap does not block Phase 2 entry

## Current Runtime State (from state.runtime.json, Phase 2 hygiene aligned)

- **round_id**: R017
- **branch**: work/canonical-mainline-repair-001
- **current_phase**: Phase 2
- **run_state**: stopped
- **last_action**: awaiting_phase2_entry_authorization
- **awaiting**: phase2_entry_authorization_for_R017

## Phase 2 Definition

| Phase | Round Range | Description |
|-------|------------|-------------|
| Phase 1 | R001-R016 | 穩定性與基礎建設 — **FORMALLY CLOSED** |
| Phase 2 | R017-R048 | 交易鏈追責與執行 — HYGIENE ALIGNED, entry pending authorization |
| Phase 3 | R049-R132 | 成熟化與 shadow 準備 |
| Phase 4 | R133-R161 | 多帳戶與營運化 |

## R017 Official Topic

Per _governance/law/161輪正式重編主題總表_唯一基準版_v2.md line 48:
- **Topic**: 秘密與金鑰管理 (Secret and Key Management)
- **Round**: R017 — first round of Phase 2
- **Phase 2 entry authorization**: NOT YET GRANTED

## R008 Replaced R010 — Formal Ruling

- R010 topic: "核心與非核心隔離" — REPLACED by R008
- R008 mode governance (cbf5091) implements "core/non-core isolation" via trading-capable vs trading-blocked mode enforcement
- R010 INVALIDATED; R008 absorbed R010's functional intent

## Lane Release & Phase 2 Status

- **Lane Release**: COMPLETED — STOP_NOW.flag removed
- **Phase 2 Entry**: NOT AUTHORIZED — awaiting explicit human authorization for R017
- **Auto-mode**: NOT AUTHORIZED — requires separate explicit human authorization

## Phase 1 Known Governance Debts

| Debt | Type | Impact |
|------|------|--------|
| R009 manifest gap | KNOWN GOVERNANCE DEBT | Functional content in canonical chain; evidence files reference old commit hash; does NOT block Phase 2 |
| ENV-001 | ENVIRONMENT WARNING | pydantic.v1 import error blocks pytest only; server.py unaffected; does NOT block Phase 2 |

## Authorization Chain

```
Phase 1 formal closure (DONE) → Lane release (DONE) → Phase 2 hygiene alignment (DONE) → R017 authorization (PENDING) → R017 construction
```

## Push Authorization Status

- **Lane Release**: COMPLETED
- **Phase 2 Entry (R017)**: NOT AUTHORIZED — requires explicit human signoff
- **Auto-mode Release**: NOT AUTHORIZED — requires separate explicit human signoff
- This document does NOT constitute Phase 2 entry authorization

---

*Last Updated: 2026-04-24*
*Status: Phase 2 hygiene aligned; R017 awaiting authorization*

---

*Last Updated: 2026-04-19*
*Status: Reference document, not governance hard rule*
