================================================================================
AUTO-MODE ROUND INPUT TEMPLATE
單輪唯一主題輸入模板
================================================================================

Version: 1.0
Status: TEMPLATE
Purpose: Standardized input for automated governance rounds

================================================================================
SECTION 1: ROUND IDENTIFICATION
================================================================================

round_id: [REQUIRED - Format: GOV-XXX or R-XXX]
  Example: GOV-HOOK-TOOLCHAIN-FIX
  Example: R-011-PERFORMANCE

task_type: [REQUIRED - Descriptive task type]
  Example: governance_hook_toolchain_fix_candidate
  Example: round_implementation

唯一主題: [REQUIRED - Single sentence describing the ONLY topic]
  Example: "修復 Windows 下 pre-push hook tool chain"
  Example: "實作 R-011 效能優化"

================================================================================
SECTION 2: LEGAL SOURCE ANCHOR
================================================================================

法源錨定:
1. 唯一輪次主題索引:
   _governance/law/161輪正式重編主題總表_唯一基準版_v2.md
2. 歷史條文正文 / 驗收與 FAIL 條件來源:
   _governance/law/03_161輪逐輪施行細則法典_整合法條增補版.docx

主題驗證:
- [ ] 主題存在於法源索引中
- [ ] 主題與法源條文一致
- [ ] 無自行改題

================================================================================
SECTION 3: SCOPE DEFINITION
================================================================================

允許修改檔案:
- [ ] file1
- [ ] file2
- [ ] file3 (最多 3-4 個核心檔案)

禁止修改檔案:
- [ ] master (絕對禁止)
- [ ] work/r016-decision-trace (絕對禁止)
- [ ] f9b6bba (絕對禁止)
- [ ] remote state (絕對禁止)
- [ ] index.js (除非本輪主題明確授權)
- [ ] run_opencode_loop.ps1 (除非本輪主題明確授權)
- [ ] config.json (除非本輪主題明確授權)
- [ ] .githooks/pre-push (除非本輪主題明確授權)
- [ ] 任何未列在「允許修改檔案」的檔案

================================================================================
SECTION 4: CONSTRAINTS
================================================================================

基本約束:
1. 嚴格依現行正式法典執行，不得自行放寬
2. 不得越權
3. 不得自行改題
4. 不得偷做下一輪
5. 不得擴大檔案修改範圍

高風險動作授權要求:
- [ ] merge → 需要人工簽字
- [ ] push → 需要人工簽字
- [ ] force-push → 需要人工簽字
- [ ] lane release → 需要人工簽字
- [ ] hook/validator 修改 → 需要人工簽字

lane 狀態:
- [ ] automation lane frozen (STOP_NOW.flag 存在)
- [ ] 不得刪除 STOP_NOW.flag
- [ ] 不得把 run_state 從 stopped 改回 active

================================================================================
SECTION 5: ACCEPTANCE CRITERIA
================================================================================

驗收條件:
A. [ ] 主題完成度檢查
B. [ ] 檔案修改範圍檢查
C. [ ] 未觸碰禁止檔案
D. [ ] 未使用 --no-verify
E. [ ] lane 維持 frozen
F. [ ] validate_evidence 通過
G. [ ] RETURN_TO_CHATGPT 欄位完整
H. [ ] 狀態碼正確
I. [ ] 證據檔案齊全

================================================================================
SECTION 6: FORMAL OUTPUT REQUIREMENTS
================================================================================

正式輸出要求:
1. 只能輸出一份完整 RETURN_TO_CHATGPT
2. 不得摘要代替正式主體
3. 所有正式結論、狀態碼、證據、修改檔案、下一步，都必須完整寫進 RETURN_TO_CHATGPT

RETURN_TO_CHATGPT 必須包含:
- round_id
- task_type
- reply_id
- status
- formal_status_code
- exact_primary_file
- exact_related_files
- files_modified
- implementation_summary
- validation_summary
- validate_evidence_executed
- validate_evidence_result
- evidence_package_files
- blockers_found
- next_action
- Plus round-specific required fields

================================================================================
SECTION 7: STATUS CODE RULES
================================================================================

狀態碼規則:

COMPLETED 條件 (ALL must be true):
- [ ] 主題完成
- [ ] 欄位完整
- [ ] 證據完整
- [ ] validate_evidence PASS
- [ ] 無越權修改
- [ ] lane 仍 frozen
- [ ] 狀態碼與正文一致
→ status = completed
→ formal_status_code = manual_review_completed (或 candidate_ready_awaiting_manual_review)

FAILED 條件 (ANY is true):
- [ ] 主題未完成
- [ ] 欄位缺失
- [ ] 證據不完整
- [ ] validate_evidence FAIL
- [ ] 越權修改
- [ ] lane 被意外解凍
- [ ] 狀態碼與正文矛盾
→ status = failed
→ formal_status_code = blocked

================================================================================
SECTION 8: EVIDENCE PACKAGE
================================================================================

必須產出的證據檔案:
- [ ] task.txt
- [ ] report.json
- [ ] evidence.json
- [ ] candidate.diff (if applicable)
- [ ] runtime/opencode_output.txt (包含 RETURN_TO_CHATGPT)

================================================================================
SECTION 9: NEXT ACTION
================================================================================

本輪完成後:
- [ ] 產出完整 RETURN_TO_CHATGPT
- [ ] 等待人工審核
- [ ] 若通過：進入下一輪或等待授權 merge/push
- [ ] 若不通過：修正後重新提交

================================================================================
END OF TEMPLATE
================================================================================