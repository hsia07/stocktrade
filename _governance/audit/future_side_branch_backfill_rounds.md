================================================================================
GOV-161 FUTURE SIDE-BRANCH BACKFILL ROUNDS — 正式補完輪次清單
================================================================================

Document ID: GOV-161-BACKFILL-ROUNDS-001
Date: 2026-04-23
Canonical Base: bf2c16f486f96b34200ccf341cbe75ec704abc9a
Source of Truth: 03_161輪逐輪施行細則法典（整合法條增補版）+ 161輪正式重編主題總表（唯一主題基準版）

================================================================================
SECTION 1: GOVERNANCE-ONLY CORRECTIONS (無需功能補完)
================================================================================

The following rounds had topic mismatches in the old v2.0 index, but NO functional
backfill is required because either:
(a) The actual implemented code already matches the correct topic (R001-R015), or
(b) The round has not yet been implemented in canonical and will use the correct
topic when implemented (R017-R161).

Phase 1 (R001-R015) — CODE ALREADY MATCHES CORRECT TOPIC:
| Round | Old Topic (v2.0) | Correct Topic (v2.1) | Backfill Needed | Reason |
|-------|------------------|----------------------|-----------------|--------|
| R001 | 基礎治理入口與執行邊界建立 | 穩定性/一致性/restore/validate/設定同步 | NO | Code audited per PHASE1-FUNCTIONAL-REALIZATION-MASTER-AUDIT |
| R002 | 啟動/停止/暫停控制基底 | 網站掛掉風險清單+防呆機制 | NO | Code audited per PHASE1-FUNCTIONAL-REALIZATION-MASTER-AUDIT |
| R003 | 狀態檔與持久化基底 | 單一真實來源 | NO | Code audited per PHASE1-FUNCTIONAL-REALIZATION-MASTER-AUDIT |
| R004 | 候選、證據、回報骨架 | 時間同步與時序一致性 | NO | Code audited per PHASE1-FUNCTIONAL-REALIZATION-MASTER-AUDIT |
| R005 | 歷史歸檔與可追溯鏈銜接 | 版本一致性與決策快照 | NO | Code audited per PHASE1-FUNCTIONAL-REALIZATION-MASTER-AUDIT |
| R006 | 控制面板完整功能落地 | 健康檢查/熔斷/降級中心 | NO | Code audited per PHASE1-FUNCTIONAL-REALIZATION-MASTER-AUDIT |
| R007 | 異常靜默保護 | 異常靜默保護 | NO | No mismatch (unchanged) |
| R008 | 狀態機與模式切換治理 | 狀態機與模式切換治理 | NO | No mismatch (unchanged) |
| R009 | 指令與任務優先級 | 指令與任務優先級 | NO | No mismatch (unchanged) |
| R010 | 啟動鏈、bridge、wrapper、actual command 對齊 | 核心與非核心隔離 | NO | Code audited per PHASE1-FUNCTIONAL-REALIZATION-MASTER-AUDIT |
| R011 | artifact、report、latest/history 產物完整化 | 效能與載入架構優化 | NO | Code audited per PHASE1-FUNCTIONAL-REALIZATION-MASTER-AUDIT |
| R012 | 決策延遲預算/AI 超時降級機制 | 決策延遲預算/AI 超時降級機制 | NO | Code audited per PHASE1-FUNCTIONAL-REALIZATION-MASTER-AUDIT |
| R013 | 實時與歷史資料分離 | 實時與歷史資料分離 | NO | No mismatch (unchanged) |
| R014 | 可觀測性統一格式 | 可觀測性統一格式 | NO | No mismatch (unchanged) |
| R015 | 多層快取策略 | 多層快取策略 | NO | No mismatch (unchanged) |

Phase 2-4 (R017-R161) — NOT YET IMPLEMENTED IN CANONICAL:
| Range | Status | Backfill Needed | Reason |
|-------|--------|-----------------|--------|
| R017-R048 | Phase 2, not implemented | NO | Will use correct topic at implementation time |
| R049-R132 | Phase 3, not implemented | NO | Will use correct topic at implementation time |
| R133-R161 | Phase 4, not implemented | NO | Will use correct topic at implementation time |

================================================================================
SECTION 2: CONFIRMED BACKFILL REQUIRED
================================================================================

| Round | Old Topic | Correct Topic | Current State | Backfill Action | Risk |
|-------|-----------|---------------|---------------|-----------------|------|
| R016 | 決策來源追溯與主張者紀錄 | 欄位命名 / API schema / 資料契約固定 | Frozen branch work/r016-decision-trace at f9b6bba implements OLD topic (DecisionTracer) | Future side branch must re-implement or re-qualify to match correct topic | HIGH |

R016 Detailed Backfill Requirement:
- Frozen Candidate: f9b6bba8b21ea53f03b0bcb2bfc690674def2b41
- Frozen Branch: work/r016-decision-trace
- Current Implementation: DecisionTracer class (decision source traceability)
- Required Implementation: Field naming / API schema / data contract fixation
- Disposition: Freeze documentation updated with topic mismatch warning.
  Branch remains frozen. Any future R016 merge attempt MUST first address
  the topic mismatch through one of:
  a) New implementation matching correct topic on clean side branch
  b) Refactoring of existing DecisionTracer to match correct topic (if semantically mappable)
  c) Deprecation of R016 candidate and creation of R016-B follow-up round

================================================================================
SECTION 3: REMAINING UNKNOWN ASSESSMENTS
================================================================================

| Round | Status | Reason |
|-------|--------|--------|
| NONE | All rounds assessed | R001-R015 code audited; R016 frozen branch audited; R017-R161 not yet in canonical |

================================================================================
SECTION 4: PERMANENTLY BLOCKED OLD SOURCE PATTERNS
================================================================================

The following old source patterns are PERMANENTLY BLOCKED for future round planning:

BLOCKED-001: Old v2.0 Topic Index
- Pattern: Any reference to "_governance/law/161輪正式重編主題總表_唯一基準版_v2.md" pre-bf2c16f version
- Block Reason: Contains 155 incorrect topics
- Replacement: Post-bf2c16f version of same file (committed in bf2c16f)

BLOCKED-002: Old v2.0 Topics in Planning Documents
- Pattern: Any document containing old topic strings such as:
  - "基礎治理入口與執行邊界建立" for R001
  - "啟動/停止/暫停控制基底" for R002
  - "決策來源追溯與主張者紀錄" for R016
  - etc.
- Block Reason: These topics do not match the law source-of-truth
- Action: Must be corrected to v2.1 topics before use

BLOCKED-003: Non-Authoritative Supplementary Sources
- Pattern: "opencode_readable_laws/05_每輪詳細主題補充法典_機器可執行補充版.md"
- Pattern: "_governance/law/readable/03"
- Block Reason: Not authoritative; may contain stale or incorrect topics
- Replacement: "opencode_readable_laws/03_161輪逐輪施行細則法典_整合法條增補版.txt"

BLOCKED-004: Candidate Branches Based on Old Topics
- Pattern: Any candidate branch or commit predating bf2c16f that references old topics
- Block Reason: Topic mismatch risk
- Exception: Frozen branches (e.g., work/r016-decision-trace) are preserved with
  explicit topic mismatch warnings but must NOT be merged without re-qualification.

================================================================================
SECTION 5: SUMMARY MATRIX
================================================================================

| Category | Count | Rounds | Action Required |
|----------|-------|--------|-----------------|
| Governance-only corrections | 160 | R001-R015, R017-R161 | None (topics corrected in index) |
| Future side-branch backfill | 1 | R016 | Re-implementation or re-qualification required |
| Unknown | 0 | — | None |
| Permanently blocked old sources | 4 patterns | All | Block and redirect to new source-of-truth |

================================================================================
END OF BACKFILL ROUNDS DOCUMENT
================================================================================
