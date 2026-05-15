# Aider 自動施工安全規則

## 文件性質
- 本文件為 04 修正版之正式補充，針對 GOV-BACKLOG-001 審計發現之 Aider 治理缺口補強。
- 本文件定義 Aider 在 stocktrade repo 中的操作範圍、限制與禁止事項。
- 優先順序：02 > 03 整合法條增補版 > 04 修正版 > 本文件 > 01。

---

## 1. Aider 路徑解析規則

### 1.1 必須只操作明確授權檔案
- Aider 只能修改當前 round task 明確授權之檔案路徑。
- 若 manifest / task.txt 未明確列出檔案路徑，Aider 不得猜測或假設。

### 1.2 同名檔案處理
- 若 repo 中存在同名檔案於不同目錄，Aider 必須確認完整路徑後再操作。
- 不得僅憑檔名推測操作對象。
- 若無法確認完整路徑，必須 blocked 並回報模糊路徑問題。

### 1.3 路徑解析優先順序
1. manifests/current_round.yaml 之 allowed_paths
2. task.txt 或 OPENCODE_START 區塊指定之路徑
3. 前一輪 evidence 之路徑
4. 上述皆不明確 → blocked，不可猜

---

## 2. Aider 小任務拆分規則

### 2.1 單次只處理一個小目標
- Aider 每次只應處理一個原子目標。
- 一個原子目標定義為：單一檔案修改、單一新增檔案、或單一驗證腳本執行。

### 2.2 禁止混合型任務
- Aider 不得在一次任務中混合以下不同類型：
  - governance 文件修改 + source code 修改
  - source code 修改 + runtime 啟動
  - hook 修改 + manifest 修改
  - evidence 建立 + source code 修改
- 混合型任務必須拆分為多個獨立子任務，逐次執行。

### 2.3 拆分原則
- 若任務需要修改超過 3 個檔案，必須評估是否需要拆分。
- 若任務涉及 governance + functional + hook + manifest 中任二類別，必須拆分。

---

## 3. Aider 負荷上限規則

### 3.1 單次檔案數上限
- Aider 單次任務不得同時處理超過 5 個檔案（新增 + 修改合計）。
- 若 task 需要超過 5 個檔案，必須拆分為多輪。

### 3.2 Context 負荷限制
- Aider 單次任務的 diff 範圍總和不得超過合理 code review 負荷（建議以 300 行為上限）。
- 若超出負荷，必須拆任務、分輪執行。

### 3.3 執行時間限制
- 若 Aider 執行時間過長（超過預期），OpenCode 應主動介入拆分或暫停。

---

## 4. Aider 禁止修改範圍

### 4.1 絕對禁止（未經明確授權）
Aider 不得修改以下檔案，除非當前 round task 明確授權：

- **正式法典**：`_governance/law/01_*`、`02_*`、`03_*`、`04_*` 以及 `161輪正式重編主題總表_唯一基準版_v2.md`
- **Git hooks**：`.githooks/` 目錄下所有檔案
- **Manifest**：`manifests/current_round.yaml`
- **Runtime state**：`automation/control/state.runtime.json`
- **Broker / Execution / Trading**：`broker/` 目錄、`server_v2.py`、`index_v2.html`
- **驗證腳本**：`scripts/validation/` 目錄下所有 Python / PowerShell 腳本
- **環境變數 / 秘密檔**：`.env`、`.env.*`、`master`

### 4.2 條件允許（需 round task 明確授權）
- **Governance 規則文件**：`_governance/stocktrade_autonomy_governance_suite/` 下之文件
- **Evidence 目錄**：`automation/control/candidates/*/` 下之 evidence.json 與 candidate.diff

### 4.3 違反處理
- 若 Aider 修改了禁止範圍檔案，該次修改無效。
- 必須 reset 該檔案至 HEAD 版本。
- 若 Aider 無法自行還原，OpenCode 必須執行 `git checkout HEAD -- <file>` 還原。

---

## 5. Aider Hook Fail 處理

### 5.1 不得使用 --no-verify
- 若 hook（pre-commit / pre-push）因 Aider 修改而失敗，不得以 `--no-verify` 跳過。
- 不得修改 hook 程式碼來繞過驗證。

### 5.2 Hook Fail 後之正確程序
1. 讀取 hook 錯誤訊息
2. 確認為 Aider 修改造成之問題
3. 修正修改內容（補 evidence、修正 manifest、調整程式碼等）
4. 重新嘗試 commit / push
5. 若無法修正，該 candidate 標示為 failed，不可 bypass

### 5.3 Aider 擴權改 Hook 之禁止
- Aider 不得為了讓自己的修改通過檢查而修改 hook 腳本。
- Aider 不得為了繞過檢查而修改驗證腳本（scripts/validation/）。

---

## 6. Aider 回報規則

### 6.1 必須產出正式 RETURN_TO_CHATGPT
- Aider 完成任務後，OpenCode 必須輸出完整 RETURN_TO_CHATGPT 區塊。
- RETURN_TO_CHATGPT 不得僅為摘要。

### 6.2 不得自行宣告可 Merge / Push
- Aider 完成修改不代表 candidate 可 merge / push。
- 必須經過 read-only manual review + user merge signoff + local no-ff merge + user push signoff + remote push + post-push reconciliation 後，才算完成。

### 6.3 回報內容至少包含
- 修改檔案清單
- 修改摘要
- 本次無修改之禁止範圍確認
- 是否 blocking / blocked
- 下一步建議

---

## 7. Aider 與 OpenCode 分工

### 7.1 OpenCode 為主要承攬人
- OpenCode 負責 governance 流程、規則判斷、授權確認、RETURN_TO_CHATGPT 輸出。
- Aider 為輔助工具，負責執行 OpenCode 指定之修改任務。

### 7.2 Aider 不得主導流程
- Aider 不得決定是否 merge / push / promote / dispatch。
- Aider 不得決定是否繞過規則。
- Aider 不得決定 law 順序或法條優先順序。

---

*本文件依 GOV-BACKLOG-001 審計結果建立。*
*建立日期：2026-05-15*
*對應 audit gap：3–5（Aider path / split / load / scope / hook fail）*
