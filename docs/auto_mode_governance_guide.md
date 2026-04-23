================================================================================
AUTO-MODE GOVERNANCE GUIDE
高風險動作必簽字對照與自動模式治理說明
================================================================================

Version: 1.0
Status: CANDIDATE
Purpose: Define high-risk actions requiring human signature in auto-mode

================================================================================
SECTION 1: HIGH-RISK ACTION SIGNATURE MATRIX
================================================================================

以下動作在自動模式下執行前，必須取得明確人工授權：

┌─────────────────────────┬──────────┬─────────────┬────────────────────────────┐
│ 動作類型                │ 風險等級 │ 必須簽字    │ 備註                        │
├─────────────────────────┼──────────┼─────────────┼────────────────────────────┤
│ git merge               │ HIGH     │ YES         │ 合併進 canonical 分支       │
│ git merge --no-ff       │ HIGH     │ YES         │ 非快轉合併                  │
│ git merge --squash      │ HIGH     │ YES         │ squash 合併                 │
├─────────────────────────┼──────────┼─────────────┼────────────────────────────┤
│ git push                │ HIGH     │ YES         │ 推送到 remote               │
│ git push --force        │ CRITICAL │ YES         │ 強制推送 (絕對禁止自行執行) │
│ git push --force-with-lease│ CRITICAL│ YES     │ 帶租約強推 (fail-closed 但仍需授權)│
├─────────────────────────┼──────────┼─────────────┼────────────────────────────┤
│ lane release            │ CRITICAL │ YES         │ 移除 STOP_NOW.flag          │
│ lane resume             │ CRITICAL │ YES         │ 恢復自動輪詢                │
│ run_state = active      │ CRITICAL │ YES         │ 改變執行狀態                │
├─────────────────────────┼──────────┼─────────────┼────────────────────────────┤
│ hook modification       │ CRITICAL │ YES         │ 修改 .githooks/pre-push     │
│ validator modification  │ CRITICAL │ YES         │ 修改 scripts/validation/*   │
│ manifest modification   │ HIGH     │ YES         │ 修改 manifests/*.yaml       │
├─────────────────────────┼──────────┼─────────────┼────────────────────────────┤
│ master branch touch     │ CRITICAL │ YES (禁止)  │ 原則上禁止，除非特殊授權    │
│ r016-decision-trace     │ CRITICAL │ YES (禁止)  │ 原則上禁止，除非特殊授權    │
│ f9b6bba touch           │ CRITICAL │ YES (禁止)  │ 原則上禁止，除非特殊授權    │
├─────────────────────────┼──────────┼─────────────┼────────────────────────────┤
│ --no-verify bypass      │ CRITICAL │ N/A (禁止)  │ 絕對禁止使用                │
│ remote state reset      │ CRITICAL │ N/A (禁止)  │ 絕對禁止自行 reset remote   │
└─────────────────────────┴──────────┴─────────────┴────────────────────────────┘

================================================================================
SECTION 2: AUTHORIZATION PROCESS
================================================================================

STEP 1: DETECTION
系統偵測到高風險動作時，立即暫停執行。

STEP 2: NOTIFICATION
系統透過以下方式通知管理員：
- Telegram Bot 推送告警訊息
- runtime/opencode_output.txt 寫入告警
- 控制台輸出紅色警告

STEP 3: REQUEST AUTHORIZATION
系統明確請求授權，格式如下：
```
⚠️ HIGH-RISK ACTION DETECTED ⚠️
Action: [動作名稱]
Risk Level: [風險等級]
Target: [目標分支/檔案]

Required: Explicit authorization to proceed.
Options:
[✅ 同意]  - Approve and proceed
[❌ 拒絕]  - Reject and abort
[⏸ 暫停]  - Pause and wait for further instructions
```

STEP 4: WAIT FOR RESPONSE
系統等待管理員回應，最長等待時間：
- Telegram: 無限等待（直到收到回應）
- 檔案輪詢: 每 2 秒檢查一次 runtime/opencode_input.txt

STEP 5: EXECUTE DECISION
- 若收到「同意」：記錄授權 → 執行動作 → 記錄結果
- 若收到「拒絕」：記錄拒絕 → 中止動作 → 報告失敗
- 若收到「暫停」：記錄暫停 → 維持暫停狀態 → 等待進一步指示

STEP 6: AUDIT LOG
所有授權決策必須記錄：
```json
{
  "timestamp": "2026-04-23T01:30:00+08:00",
  "action": "merge",
  "decision": "approve",
  "authorized_by": "human_admin",
  "round_id": "GOV-XXX",
  "reason": "Verified candidate ready for merge"
}
```

================================================================================
SECTION 3: AUTOMATIC BLOCK CONDITIONS
================================================================================

以下情況系統必須自動 BLOCK，不得等待授權：

BLOCK CONDITION 1: --no-verify Detected
- 原因: 繞過 hook 驗證
- 動作: 立即停止，報告 "hook_bypass_detected"

BLOCK CONDITION 2: master Branch Modification
- 原因: master 不是合法工作基線
- 動作: 立即停止，報告 "master_protection_violation"

BLOCK CONDITION 3: r016 Branch Modification
- 原因: R016 candidate 已凍結
- 動作: 立即停止，報告 "r016_frozen_violation"

================================================================================
SECTION 3A: FROZEN BRANCH REGISTRY (凍結分支登記簿)
================================================================================

以下分支已經正式凍結，任何修改嘗試都必須自動 BLOCK：

┌────────────────────────┬────────────────────────────────────────────────────┐
│ 屬性                    │ work/r016-decision-trace                           │
├────────────────────────┼────────────────────────────────────────────────────┤
│ 凍結狀態                │ FORMALLY FROZEN                                    │
│ 凍結日期                │ 2026-04-23                                         │
│ 凍結文件                │ _governance/frozen/R016-work-r016-decision-trace-  │
│                         │ freeze.md                                          │
│ 凍結候選                │ f9b6bba8b21ea53f03b0bcb2bfc690674def2b41          │
│                         │ "R016: Decision source traceability -              │
│                         │  DecisionTracer class"                             │
│ 審計時 HEAD             │ 3586a07                                            │
│ 主題                    │ R016 - 決策來源追溯與主張者紀錄                     │
│ 凍結原因                │ Branch contamination (mixed rounds R-006~R-015     │
│                         │ + GOV commits)                                     │
│ 不可刪除原因            │ 保留 R016 候選實作，供未來 cherry-pick 恢復        │
├────────────────────────┼────────────────────────────────────────────────────┤
│ 禁止動作                │ MERGE into canonical → ABSOLUTELY PROHIBITED       │
│                         │ DELETE branch → ABSOLUTELY PROHIBITED              │
│                         │ MODIFY contents → PROHIBITED                       │
│                         │ REBASE / REWRITE → ABSOLUTELY PROHIBITED           │
│                         │ FORCE-PUSH → ABSOLUTELY PROHIBITED                 │
├────────────────────────┼────────────────────────────────────────────────────┤
│ 未來恢復路徑            │ 1. 從 canonical HEAD 開新乾淨分支                  │
│                         │ 2. 只 cherry-pick f9b6bba                          │
│                         │ 3. 驗證無污染                                      │
│                         │ 4. 按標準治理流程提交為新候選                       │
│                         │ 5. 永遠不可重用被污染的原分支                       │
└────────────────────────┴────────────────────────────────────────────────────┘

FROZEN BRANCH POLICY:
1. 凍結分支不得以任何理由 merge 進 canonical
2. 凍結分支不得刪除（保留候選參考與審計追蹤）
3. 凍結分支的歷史不得以 rebase/rewrite 修改
4. 凍結分支不得以 force-push 推送到 remote
5. 未來恢復只能走「新乾淨分支 + cherry-pick 候選 commit」
6. 任何違反凍結規則的行為必須觸發 STOP condition 6.4

BLOCK CONDITION 4: Cross-Round Topic Change
- 原因: 本輪主題被擅自更改
- 動作: 立即停止，報告 "topic_changed_mid_round"

BLOCK CONDITION 5: File Scope Expansion
- 原因: 修改了未授權的檔案
- 動作: 立即停止，報告 "unauthorized_file_modification"

BLOCK CONDITION 6: Missing Required Fields
- 原因: RETURN_TO_CHATGPT 缺少必要欄位
- 動作: 報告 "incomplete_return_to_chatgpt"，等待修正

BLOCK CONDITION 7: Status Code Contradiction
- 原因: 狀態碼與正文內容矛盾
- 動作: 報告 "status_content_contradiction"，等待修正

================================================================================
SECTION 4: LANE RELEASE PREREQUISITES
================================================================================

在正式釋放 automation lane (移除 STOP_NOW.flag) 之前，必須滿足：

PREREQUISITE 1: Infrastructure Verification
- [ ] Hook toolchain: Windows 可執行且 fail-closed
- [ ] Pre-push validation: GOV path / R path / malformed path 皆通過
- [ ] No --no-verify dependency
- [ ] config.json: simulation.enabled = false
- [ ] run_opencode_loop.ps1: 使用 real CLI mode

PREREQUISITE 2: Bridge Verification
- [ ] index.js: Telegram bot 配置正確
- [ ] Approval flow: approve / reject / pause 按鈕正常運作
- [ ] Polling loop: 每 2 秒檢查 input 檔案
- [ ] Output writing: 結果正確寫入 output 檔案

PREREQUISITE 3: Runtime Hygiene
- [ ] runtime/opencode_input.txt: 0 bytes或正確初始化
- [ ] runtime/opencode_output.txt: 0 bytes或正確初始化
- [ ] 無殘留測試內容
- [ ] runtime/ 目錄存在且可寫入

PREREQUISITE 4: Governance Lock Files
- [ ] review_memory.txt: 已建立且內容完整
- [ ] templates/auto_mode_round_input.md: 已建立
- [ ] docs/auto_mode_governance_guide.md: 已建立 (本檔案)

PREREQUISITE 5: Testing Completed
- [ ] 至少一輪完整的 governance round end-to-end 測試
- [ ] Hook validation 在 Windows 環境測試通過
- [ ] Bridge polling loop 測試通過
- [ ] 高風險簽字閘門測試通過
- [ ] 緊急停機條件測試通過

PREREQUISITE 6: Monitoring Ready
- [ ] STOP_NOW.flag 機制: 測試凍結/恢復
- [ ] Error alerting: 錯誤時能正確告警
- [ ] Audit trail: 所有動作有日誌記錄
- [ ] Remote state monitoring: 能偵測 remote 異常變更

PREREQUISITE 7: Documentation
- [ ] 操作手冊: 管理員知道如何操作
- [ ] 故障排除: 常見問題有解決方案
- [ ] 回滾計畫: 出問題時知道如何回滾

================================================================================
SECTION 5A: PHASE 1 CLOSURE DECLARATION (Phase 1 正式收口宣告)
================================================================================

PHASE 1 STATUS: FORMALLY CLOSED
Closure Date: 2026-04-23
Closure Document: _governance/closure/phase1-formal-closure-declaration.md

Phase 1 範圍：R001 – R016（依 161輪正式重編主題總表_唯一基準版_v2.md）

收口依據：
- PHASE1-CLOSURE-READINESS-AUDIT-RERUN (PHASE1-AUDIT-RERUN-001)
- 確認 phase1_closure_ready = true
- 確認 remaining_phase1_blockers = []
- R016 透過 formal freeze 完成收口（凍結文件已進 canonical/remote；主題已依 v2.1 校正為「欄位命名 / API schema / 資料契約固定」）

────────────────────────────────────────────────────────────────────────
⚠️ 關鍵區分：Phase 1 Closed ≠ Lane Release Authorized ⚠️
────────────────────────────────────────────────────────────────────────

「Phase 1 收口完成」僅代表 R001–R016 的交付物已齊備或已正式凍結。
不代表以下事項獲得授權：

┌────────────────────────┬──────────────────────────────────────────────┐
│ 事項                    │ 狀態                                         │
├────────────────────────┼──────────────────────────────────────────────┤
│ Phase 1 Closure        │ ✅ FORMALLY CLOSED                           │
│ Lane Release           │ ❌ NOT AUTHORIZED (STOP_NOW.flag present)    │
│ Auto-Mode Release      │ ❌ NOT AUTHORIZED (blockers remain)          │
│ Promotion to master    │ ❌ NOT AUTHORIZED (master not valid baseline)│
│ Phase 2 Startup        │ ❌ NOT AUTHORIZED (requires separate auth)   │
└────────────────────────┴──────────────────────────────────────────────┘

remaining_lane_release_blockers:
- LR-001: runtime/opencode_output.txt residual (14115 bytes)
- LR-002: runtime enforcement gap (documentation-only locks)
- LR-003: no end-to-end auto-mode testing
- LR-004: stale state.runtime.json

auto_mode_release_allowed_now = false
lane_release_ready_now = false

Lane release 必須另案處理，不得與 Phase 1 closure 混為一談。

================================================================================
SECTION 5: POST-RELEASE MONITORING
================================================================================

Lane 釋放後，系統必須持續監控：

MONITORING 1: Round Topic Consistency
- 每輪開始時驗證主題是否與法源索引一致
- 不一致 → 暫停並告警

MONITORING 2: File Scope Compliance
- 每輪結束時驗證修改檔案是否在授權範圍內
- 越權 → 暫停並告警

MONITORING 3: Hook Integrity
- 每次 push 前驗證 hook 是否正常執行
- Hook 失敗 → 阻止 push 並告警

MONITORING 4: Remote State Consistency
- 定期比對 local 與 remote HEAD
- 不一致 → 暫停並告警

MONITORING 5: Lane State
- 定期檢查 STOP_NOW.flag 狀態
- 意外消失 → 立即恢復並告警

================================================================================
END OF GOVERNANCE GUIDE
================================================================================