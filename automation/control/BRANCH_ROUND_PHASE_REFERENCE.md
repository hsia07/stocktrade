# Branch / Round / Phase / Runtime Reference

## Canonical Mainline

- **Current Mainline**: `work/canonical-mainline-repair-001`
- **Legal Status**: Verified baseline for R-006 (Health Check / Circuit Breaker / Degradation Center)
- **State Sync**: Completed with zero drift

## Branch Naming Reference

| Branch | Round Reference | Legal Status | Note |
|--------|-----------------|--------------|------|
| work/canonical-mainline-repair-001 | R-006 | CANONICAL MAINLINE | Currently verified |
| work/r006-governance | R-006 | HISTORICAL WORK | Base point, superseded |
| work/r007-silence-protection | R-007 | WORK (not merged) | R-007 complete but not merged |
| work/r008-state-machine-governance | R-008 | WORK (not merged) | R-008 complete but not merged |
| work/r009-command-priority | R-009 | WORK (not merged) | R-009 complete but not merged |
| candidates/R-015 | R-006~R-015 | CANDIDATE STALLED | Multi-round attempt, stalled |
| candidates/R-010~R-014 | R-010~R-014 | INVALIDATED |废止 |
| master | N/A | PROTECTED | No direct push allowed |

## Key Distinctions

- **round_id**: The specific round being executed (e.g., R-006)
- **branch**: The Git branch where work happens
- **phase**: The Phase grouping (Phase 1 = R-001~R-015)
- **runtime snapshot**: The current execution state in state.runtime.json

## Current Runtime State (from state.runtime.json)

- round_id: R-006
- branch: work/canonical-mainline-repair-001
- current_phase: Phase 1
- run_state: stopped
- last_action: r006_purified_validation_completed

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

---

*Last Updated: 2026-04-19*
*Status: Reference document, not governance hard rule*