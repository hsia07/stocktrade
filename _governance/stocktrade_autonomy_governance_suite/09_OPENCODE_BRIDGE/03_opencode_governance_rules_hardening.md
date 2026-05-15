# OpenCode 自動施工安全規則補強版

## 文件性質
- 本文件為 04 修正版之正式補充，針對 GOV-BACKLOG-001 審計發現缺口補強。
- 本文件將 GOV-INT-003 實際執行之治理慣例正式寫入 repo。
- 優先順序：02 > 03 整合法條增補版 > 04 修正版 > 本文件 > 01。

---

## 1. 禁止 Bundled Approval

### 1.1 合併、推送、推後對帳不得一次授權
- merge、push、post-push reconciliation 為三個獨立步驟，各步驟均須使用者分別明確簽字。
- 使用者回覆 "approve" 或 "同意" 或 "繼續" 或 "yes" 僅得解讀為同意**當下步驟**，不得解讀為同意後續所有步驟。
- OpenCode 不得將單一 "approve" 擴張解釋為 merge + push + reconciliation 一次授權。

### 1.2 固定流程
每輪正式 candidate 從建立到 remote 就緒必須依序經過以下步驟，缺一不可：

```
candidate creation
    ↓
read-only manual review (by user or formal review round)
    ↓
user local no-ff merge signoff (explicit, separate)
    ↓
local no-ff merge
    ↓
user remote push signoff (explicit, separate)
    ↓
remote push
    ↓
post-push reconciliation (read-only verification)
```

- 任一階段不得跳過。
- 任一階段不得與前一階段合併授權。
- push 完成後若未執行 post-push reconciliation，不得視為已安全推送。

---

## 2. 禁止 --no-verify

### 2.1 不得使用
- `git commit --no-verify`、`git push --no-verify`、或任何等價跳過 hook 驗證之行為，一律禁止。
- 此禁止適用於 OpenCode、Aider、ChatGPT 所下達之指令，以及任何手動操作。

### 2.2 Hook Fail 處理
- 若 hook 執行失敗（pre-commit / pre-push 任一檢查未通過），不得以 --no-verify 補救。
- Hook fail 之正確處理程序：
  1. 讀取 hook 錯誤訊息，確認具體失敗原因
  2. 修正程式碼、證據、manifest 或其他可修正項目
  3. 重新執行 commit / push，讓 hook 重新檢查
  4. 若無法修正，則該 candidate 標示為 blocked，不得 bypass

### 2.3 例外
- 無例外。--no-verify 在任何情境下均不得使用。

---

## 3. 禁止 Force Push

### 3.1 --force / --force-with-lease 均禁止
- `git push --force`、`git push --force-with-lease`、或任何等價覆蓋 remote 歷史之行為，一律禁止。
- 此禁止適用於所有 branch，包括 candidate branch 與 canonical branch。

### 3.2 例外
- 僅在以下條件全部成立時，可經使用者明確簽字後使用 force push：
  - 已有正式 incident containment 程序啟動
  - 使用者書面指明允許 force push 之 commit 範圍與原因
  - force push 僅限於 candidate branch，不得用於 canonical branch

---

## 4. 禁止 Governance 階段啟動 Runtime

### 4.1 適用階段
以下階段不得啟動任何 runtime 程序（main_control_loop、start_loop、trading、broker、execution、live）：

- read-only manual review
- merge（含 merge 前準備與 merge 執行）
- push（含 push 前檢查與 push 執行）
- post-push reconciliation

### 4.2 禁止事項
- 不得啟動 main_control_loop.ps1
- 不得執行 start_loop.ps1
- 不得設定 order_execution_allowed = TRUE
- 不得啟動 trading_core / broker / execution / live 程序
- 不得重啟 control_bridge 或 telegram_sidecar
- 不得 dispatch 任何 functional round（R020–R161）

### 4.3 Runtime 僅能在以下階段啟動
- 已由使用者簽字 dispatch 之 functional round
- 已確認 chain_status 為 backlog_merged_ready_for_next_dispatch 或等價可 dispatch 狀態
- 已由使用者在 round 開頭明確簽字同意開始

---

## 5. RETURN_TO_CHATGPT 正式主體輸出規則

### 5.1 性質
RETURN_TO_CHATGPT 不是摘要區，而是正式主體輸出區。凡足以影響輪次判定、candidate 狀態、approve / promote / merge、blocked、failed、candidate_ready、修法成立與否或下一步流程之資訊，均必須完整寫入 RETURN_TO_CHATGPT。

### 5.2 最低必備欄位
每份 RETURN_TO_CHATGPT 輸出至少應包含：

```
round_id:
  <唯一輪次識別碼>

task_type:
  <任務類型>

status:
  completed / blocked / failed

formal_status_code:
  <正式狀態碼>

candidate_branch:
  <若有 candidate>

candidate_commit:
  <若有 candidate>

expected_base_head:
  <若有 base>

files_modified:
  <實際修改檔案清單，或 NONE>

evidence_json_path:
  <若有 evidence>

(prohibited action flags block)
main_control_loop_started_true_or_false:
  FALSE / TRUE
r030_dispatch_started_true_or_false:
  FALSE / TRUE
merge_executed_true_or_false:
  FALSE
push_executed_true_or_false:
  FALSE
force_push_used_true_or_false:
  FALSE
no_verify_used_true_or_false:
  FALSE

remaining_blockers:
  NONE 或逐項列出

recommended_next_action:
  <下一步建議>

final_recommendation:
  <最終建議>
```

### 5.3 前文不得比 RETURN_TO_CHATGPT 更完整
- 若前文說明、分段敘述、表格或人類可讀內容比 RETURN_TO_CHATGPT 承載更多關鍵結論，視為正式輸出無效。
- 整份回報應退回重做，不得作為驗收、排程、candidate 核准、promotion、人工審核或輪次推進之依據。

### 5.4 唯一正式依據
- 任何代理、排程器、人工審核官、驗收腳本或面板，於正式判讀時，應以完整且有效之 RETURN_TO_CHATGPT 為唯一正式主體輸出依據。
- 前文僅供輔助閱讀，不得取代之。

---

## 6. R030 Readiness PASS 不等於 Dispatch 授權

### 6.1 分離原則
- R030 readiness preflight PASS 僅代表 R030 具備 dispatch 前置條件，不代表 R030 已被授權 dispatch。
- R030 dispatch 必須由使用者在 preflight PASS 後，另外以明確文字簽字同意。

### 6.2 Chain Status 約束
- 若 chain_status 不是 backlog_merged_ready_for_next_dispatch 或等價 ready 狀態，不得 dispatch R030。
- 若 current_round 不是 NONE，不得 dispatch R030。
- 若 manifest_last_completed_round 不是 R029，不得 dispatch R030。

---

## 7. 禁止 OpenCode 自行擴權

### 7.1 OpenCode 不得自行：
- 宣判通過（pass 必須經正式 review）
- 修改法典母表標準
- 偷加未經核准的新要求
- 修改正式法典 01 / 02 / 03 / 04 本體
- 修改 .githooks/
- 修改 scripts/validation/
- 修改 automation/control/state.runtime.json

### 7.2 若 OpenCode 發現任何上述修改需求
- 必須建立 formal candidate
- 必須經過 read-only manual review
- 必須由使用者簽字方可合併

---

*本文件依 GOV-BACKLOG-001 審計結果建立，將 GOV-INT-003 執行慣例正式寫入 repo。*
*建立日期：2026-05-15*
*對應 audit gap：1–8*
