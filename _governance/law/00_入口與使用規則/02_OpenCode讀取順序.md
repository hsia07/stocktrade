# OpenCode 讀取順序與使用規範

## 標準讀取順序（三步驟）

### 第一步：讀取基準檔
**檔案**：`CURRENT_GOVERNANCE_BASELINE.md`（repo 根目錄）

**目的**：
- 確認當前治理基準
- 確認當前正式輪次
- 確認輪次主題與狀態

---

### 第二步：讀取法典優先順序
**檔案**：`_governance/law/00_入口與使用規則/01_法典優先順序.md`

**目的**：
- 確認四份正式法典之位階關係
- 確認母表（02）> 細則（03）> 補強（04）> 白話（01）
- 確認 03_強化法條版為歷史底稿，非現行正式法典

---

### 第三步：讀取該輪所需正式法典

依判斷類型選擇對應法典：

| 判斷類型 | 必須讀取檔案 |
|----------|--------------|
| **全域硬規則** | `02_交易系統極限嚴格母表法典.docx` |
| **單輪驗收** | `03_161輪逐輪施行細則法典_整合法條增補版.docx`（該輪章節） |
| **證據規範** | `04_交易系統法典補強版_20260416_修正版.md` + `validate_evidence.ps1` |
| **入門理解** | `01_系統白話總覽與功能說明.docx`（僅供參考，不得做判定依據） |

---

## 具體使用規範

### 判斷全域硬規則時

**優先讀取**：`02_交易系統極限嚴格母表法典.docx`

**適用場景**：
- 是否可進下一輪
- 是否可碰 master
- 是否可跳輪
- 是否可自動 merge
- 最終爭議裁定

**禁止**：以 01 白話總覽或 04 補強版凌駕 02 母表規則

---

### 判斷單輪是否可 candidate 時

**必須動作**：
1. 確認 CURRENT_GOVERNANCE_BASELINE.md 當前輪次
2. 讀取 03 該輪完整法條（不可只看摘要或前文說明）
3. 逐條核對該輪法條要求是否全部滿足
4. **缺一不可**：若有任何法條未滿足，不得標記 candidate_ready

**禁止**：
- 只看回報摘要就判定輪次通過
- 只看前文說明就判定輪次通過
- 只看 01 白話總覽就判定輪次通過
- 以「前面已說過」為由省略法條重讀

---

### 判斷單輪是否可 merge 時

**必須動作**：
1. 重新讀取 repo 實際檔案（不可只看回報摘要）
2. 依 03 該輪完整法條逐條重新審核
3. 確認所有交付物真實存在且符合規範
4. 確認 validate_evidence.ps1 為 PASS

**禁止**：
- 只看前文說明或摘要就同意 merge
- 未重讀法條就憑回報判定
- 以工具方便性代替法條滿足度判定

---

### 判斷證據規範時

**可參考**：`04_交易系統法典補強版_20260416_修正版.md`

**適用場景**：
- evidence package 格式
- validate_evidence.ps1 執行規範
- candidate/merge 流程細則
- 補充 02/03 未明載之治理要求

**限制**：若 04 與 02/03 衝突，以 02/03 為準

---

## 禁止事項

### 不得只靠摘要或前文說明
- ❌ 「前面比較完整，這裡只給摘要」
- ❌ 「前文已說明，不再重複」
- ❌ 「依之前回報，本輪已通過」

### 不得只看白話總覽
- ❌ 只看 01 就判定輪次通過
- ❌ 以 01 的簡化說明代替 02/03 的嚴格條文

### 不得省略法條重讀
- ❌ 「該輪法條與上輪類似，不再重讀」
- ❌ 「依多輪預製模式，R+1 完成表示 R 已收口」

---

## 驗證自我檢查清單

OpenCode 在回報 candidate_ready / merge_approved 前，必須自檢：

- [ ] 已讀 CURRENT_GOVERNANCE_BASELINE.md 確認當前輪次
- [ ] 已讀 01_法典優先順序.md 確認位階關係
- [ ] 已依判斷類型讀取對應法典（02 全域 / 03 單輪 / 04 補充）
- [ ] 判單輪時，已完整讀取 03 該輪全部條文（非摘要）
- [ ] 已逐條核對法條要求，確認全部滿足
- [ ] 已執行 validate_evidence.ps1 且結果為 PASS
- [ ] 回報內容與法條要求一一對應，無遺漏
- [ ] 無授權外修改（如混入第 10+ 輪內容）

---

## 歷史檔案處理

**03_161輪逐輪施行細則法典_強化法條版.docx**：

若需參考，必須：
1. 明確標示為「歷史底稿 / historical base / superseded」
2. 同時對照 03_整合法條增補版確認條文有效性
3. 不得以之做為輪次判定之單一依據

---

## OpenCode 可讀版優先讀取指引

### 可讀版目的

為解決 .docx 二進制檔案無法直接讀取之技術限制，現行正式法典已建立 **Markdown 可讀版鏡像**：

**位置**：`_governance/law/readable/`

### 可讀版檔案清單

| 檔名 | 路徑 | 用途 |
|------|------|------|
| 01_系統白話總覽 | `_governance/law/readable/01_系統白話總覽與功能說明.md` | 快速理解 |
| 02_母表法典 | `_governance/law/readable/02_交易系統極限嚴格母表法典.md` | 全域硬規則 |
| 03_逐輪施行細則 | `_governance/law/readable/03_161輪逐輪施行細則法典_整合法條增補版.md` | 單輪條文 |
| 03_R7-R9_節錄 | `_governance/law/readable/03_R7-R9_正式審核可讀節錄.md` | **R7-R9 審核專用** |
| 04_補強版 | `_governance/law/readable/04_交易系統法典補強版_20260416_修正版.md` | 治理補充 |

### R7-R9 正式審核讀取順序

審核 R-007 / R-008 / R-009 時，**優先讀取**：

1. `_governance/law/readable/03_R7-R9_正式審核可讀節錄.md`
2. 對照 `_governance/law/readable/03_161輪逐輪施行細則法典_整合法條增補版.md` 完整條文
3. 依節錄逐條審核該輪要求

⚠️ **重要**：可讀版僅為鏡像，若與正式法源衝突，以正式法源為準。

---

## 檔案路徑速查

| 檔名 | 正式法源路徑 | 可讀版路徑 |
|------|--------------|------------|
| CURRENT_GOVERNANCE_BASELINE.md | repo 根目錄 | - |
| 00_README.md | `_governance/law/00_入口與使用規則/00_README.md` | - |
| 01_法典優先順序.md | `_governance/law/00_入口與使用規則/01_法典優先順序.md` | - |
| 02_母表法典 | `_governance/law/02_*.docx` | `_governance/law/readable/02_*.md` |
| 03_逐輪施行細則 | `_governance/law/03_*.docx` | `_governance/law/readable/03_*.md` |
| 04_補強版 | `_governance/law/04_*.md` | `_governance/law/readable/04_*.md` |
| 01_白話總覽 | `_governance/law/01_*.docx` | `_governance/law/readable/01_*.md` |

---

## Phase 級主核心 Merge 判定時

### 判定是否可進行 Phase 級主核心 merge 前，必須依序讀取：

1. **CURRENT_GOVERNANCE_BASELINE.md** - 確認當前 Phase 收口狀態與主核心 merge 規則
2. **04 補強版第 12 節** - Phase 級主核心 Merge 治理法典（第 49–58 條）
3. **work branch 實際狀態** - 確認該 Phase 預定納入輪次是否皆已收口到 work branch
4. **各輪狀態清查** - 確認是否仍存在 candidate only / review only / technical_unfinished / blocked 之輪次

### 必須確認 checklist：

- [ ] 該 Phase 預定納入輪次是否皆已收口到 work branch
- [ ] 是否仍存在未完成狀態之輪次（candidate only / review only / technical_unfinished / blocked）
- [ ] 是否已完成 Phase 級總審核
- [ ] 是否已取得使用者明示簽字同意

### OpenCode 強制停止點：

到達 Phase 級主核心 merge 決策點時，**OpenCode 必須立即停止**，不得提供主核心 merge 指令，等待使用者明示簽字。

---

## Shell / Git 非互動執行判定時

### 執行 merge / push / switch / verify 前必須確認：

1. **非互動參數** - merge 必須使用 `--no-edit --no-ff`，不得打開 editor、pager
2. **前置檢查** - 先執行 `git rev-parse --verify` 確認分支存在
3. **狀態檢查** - 先執行 `git status --porcelain=v1` 確認工作目錄狀態
4. **超時保護** - 設定 15 秒超時上限，超過立即停止

### 執行中強制停止條件：

| 狀況 | 必須動作 | 回報狀態碼 |
|------|----------|------------|
| 超過 15 秒無結果 | 立即停止 | technical_unfinished |
| merge conflict | 立即 `git merge --abort` | technical_unfinished |
| 任何失敗 | 完整回報 command + stdout + stderr + failure_point | blocked / technical_unfinished |

### 禁止事項：

- ❌ 等待人工輸入或「思考中」無限掛起
- ❌ 自行交互式修復衝突
- ❌ 多輪猜測式 shell 嘗試
- ❌ 省略非互動參數

---

*最後更新：2026-04-16*
