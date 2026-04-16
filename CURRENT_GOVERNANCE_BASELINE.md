# 現行治理基準 / CURRENT_GOVERNANCE_BASELINE

## 法源優先順序

### 現行正式法典四檔路徑

| 優先順序 | 檔名 | 路徑 | 位階說明 |
|----------|------|------|----------|
| 1 | **交易系統極限嚴格母表法典** | `_governance/law/02_交易系統極限嚴格母表法典.docx` | 母表硬法（最高優先） |
| 2 | **161輪逐輪施行細則法典** | `_governance/law/03_161輪逐輪施行細則法典_整合法條增補版.docx` | 逐輪施行細則 |
| 3 | **交易系統法典補強版 2026-04-16** | `_governance/law/04_交易系統法典補強版_20260416_修正版.md` | 補強版（補充規則） |
| 4 | **系統白話總覽** | `_governance/law/01_系統白話總覽與功能說明.docx` | 白話導覽（輔助參考） |
| - | **本次任務補充規則** | 當次指令 | 單次任務特別規則 |

### 法典入口與使用規則

- **法典入口目錄**：`_governance/law/00_入口與使用規則/`
- **法典優先順序說明**：`_governance/law/00_入口與使用規則/01_法典優先順序.md`
- **OpenCode 讀取順序**：`_governance/law/00_入口與使用規則/02_OpenCode讀取順序.md`

### OpenCode 可讀版（鏡像 - MIRROR ONLY）

**目錄**：`_governance/law/readable/`

| 檔名 | 對應正式法典 | 用途 |
|------|--------------|------|
| `01_系統白話總覽與功能說明.md` | `01_系統白話總覽與功能說明.docx` | OpenCode 可讀版本 |
| `02_交易系統極限嚴格母表法典.md` | `02_交易系統極限嚴格母表法典.docx` | OpenCode 可讀版本 |
| `03_161輪逐輪施行細則法典_整合法條增補版.md` | `03_161輪逐輪施行細則法典_整合法條增補版.docx` | OpenCode 可讀版本 |
| `03_R7-R9_正式審核可讀節錄.md` | - | R7-R9 審核專用節錄版 |
| `04_交易系統法典補強版_20260416_修正版.md` | `04_交易系統法典補強版_20260416_修正版.md` | OpenCode 可讀版本 |

**重要聲明**：
- ✅ **可讀版僅供 OpenCode 自動審核使用**，方便 LLM 讀取
- ✅ **可讀版為鏡像性質**，內容與正式法典一致
- ❌ **可讀版不得取代正式法典四檔**（docx/md 維持正式法源地位）
- ❌ **不得以「可讀版未同步」為由拒絕執行正式法典**
- ⚠️ **若有疑義，以正式法典（docx/md）為準**

### 法典使用規範

1. **母表硬法（02）**：全域性、跨輪次、不可繞過之硬規則，最高位階
2. **逐輪施行細則（03）**：單輪具體條文、驗收標準、交付要求
3. **補強版（04）**：補充 02/03 未明載之治理規則，**不得取代 02/03**
4. **白話總覽（01）**：輔助理解，**OpenCode 不得作為正式輪次判定依據**

### 重要提醒

- 判全域硬規則時，**優先讀 02**
- 判單輪是否 candidate/merge 時，**必須回讀 03 該輪完整條文**
- 若有衝突，以**較嚴格、較可驗收、較可追責、較不可繞過**者優先

---

## 目前正式輪次

- **當前輪次**: 第 6 輪 (R-006)
- **禁止跳輪**: 不准進第 7 輪

---

## 第 6 輪唯一主題

**健康檢查 / 熔斷 / 降級中心**

---

## Round 6 現況

| 項目 | 狀態 |
|------|------|
| 驗收狀態 | **未通過 / 待重驗** |
| 舊版驗收 | ~~PASS~~ (已失效，主題不同) |
| 現行主題 | 健康檢查 / 熔斷 / 降級中心 |

---

## 歷史狀態標記

- **ROUND6_ACCEPTANCE.md**: 已標記為舊版/失效/待重驗
- **舊版主題**: 模式契約 + PnL統一計算
- **關鍵聲明**: 舊版 PASS 不再等於現行 Round 6 pass

---

## 候選證據守門機制 (HARD GATE)

### ⚠️ 硬規則

1. **未執行 validate_evidence.ps1，不得標記 candidate_ready**
2. **validate_evidence.ps1 驗證失敗時，只能回報 technical_unfinished / blocked**
3. **只有 validate_evidence.ps1 通過後，才可回報 candidate_ready**

### 證據驗證工具
- **腳本**: `scripts/validation/validate_evidence.ps1`
- **用途**: 檢查任務是否產出完整證據包
- **性質**: HARD GATE - candidate_ready 的必要條件

### Candidate Ready 硬前提

#### 必要條件（缺一不可）
1. ✅ **已執行 validate_evidence.ps1**
2. ✅ **validate_evidence.ps1 回傳 PASS**
3. ✅ **證據包完整**：
   - `task.txt` - 任務描述文件
   - `aider.log` - Aider 執行日誌
   - `candidate.diff` - 代碼變更 diff
   - `report.json` - 執行報告
4. ✅ **Git 狀態可查**：
   - `git status --short`
   - `git diff --name-only`
5. ✅ **測試證據**（若本輪有指定）

#### 禁止事項
- ❌ 未執行驗證就標記 candidate_ready
- ❌ 驗證失敗仍標記 completed
- ❌ 驗證失敗不回報正式狀態碼

### 使用方式
```powershell
# 標準驗證（必須執行）
.\scripts\validation\validate_evidence.ps1 -CandidateId "TASK-001"

# 嚴格模式
.\scripts\validation\validate_evidence.ps1 -CandidateId "TASK-001" -StrictMode

# 指定測試證據
.\scripts\validation\validate_evidence.ps1 -CandidateId "TASK-001" -RequiredTests @("tests/test_feature.py")
```

### 驗證結果判定與強制狀態碼

| 驗證結果 | 可標記狀態 | 強制回報狀態碼 |
|----------|------------|----------------|
| **PASS** | candidate_ready | candidate_ready_eligible |
| **FAIL - 缺證據** | ❌ 不可 | **technical_unfinished** |
| **FAIL - 安全問題** | ❌ 不可 | **blocked** |
| **未執行** | ❌ 不可 | **technical_unfinished** |

---

## Candidate 前完整重審義務

### 判定 candidate_ready 前，必須依該輪完整法條重新審核

**禁止事項**：
- ❌ 只看回報摘要或前文說明就判定輪次通過
- ❌ 只看 01 白話總覽就判定輪次通過
- ❌ 以「前面已說明」為由省略法條重讀

**必須動作**：
1. 讀取 CURRENT_GOVERNANCE_BASELINE.md 確認當前輪次
2. 讀取 `_governance/law/00_入口與使用規則/01_法典優先順序.md` 確認位階
3. **完整讀取 03 該輪全部條文**（不可只看摘要）
4. 逐條核對該輪法條要求是否全部滿足
5. **缺一不可**：若有任何法條未滿足，不得標記 candidate_ready
6. 執行 validate_evidence.ps1 並確認 PASS
7. 確認證據包完整且無 fabricated evidence

---

## Merge 前完整重審義務

### 核准 Merge 前，必須重新讀取 repo 實際檔案並依該輪法條重新審核

**禁止事項**：
- ❌ 只看回報摘要就同意 merge
- ❌ 未重讀法條就憑回報判定
- ❌ 以工具方便性代替法條滿足度判定

**必須動作**：
1. 重新讀取 repo **實際檔案**（不可只看回報摘要或前文說明）
2. 依 03 **該輪完整法條逐條重新審核**
3. 確認所有交付物真實存在且符合規範
4. 確認 validate_evidence.ps1 為 PASS
5. 確認無授權外修改
6. 確認 merge 後不會破壞審計鏈

### 流程觸發點

```
任務完成
    ↓
執行 validate_evidence.ps1（強制）
    ↓
├─ PASS → 可回報 candidate_ready
└─ FAIL → 回報 technical_unfinished / blocked
```

---

## 固定證據包回報模板

每次任務必須回報：

```
### Evidence Package
- candidate_id: {id}
- candidate_branch: {branch}
- commit_hash: {hash}

### Required Files Check
- [ ] task.txt
- [ ] aider.log
- [ ] candidate.diff
- [ ] report.json

### Git Status
- modified_files: {count}
- untracked_files: {count}
- working_tree_clean: {yes/no}

### Test Evidence
- test_files: {list}
- test_passed: {count}/{total}

### Validation Result
- status: {PASS/FAIL}
- can_mark_candidate_ready: {true/false}
- missing_evidence: {list}
```

---

## 歷史檔案處理規則

### 03_強化法條版（非現行正式法典）

**檔案**：`03_161輪逐輪施行細則法典_強化法條版.docx`（若存在）

**性質**：歷史底稿 / historical base / superseded

**狀態**：
- ❌ **非現行正式法典**
- ❌ **不得以之做為輪次判定依據**
- ✅ 僅供參考，若需引用必須同時對照 03_整合法條增補版確認有效性

**存放建議**：
- 可移至 `_governance/law/archive/` 或 `_governance/law/historical/`
- 或保留原位但明確標示為 superseded

---

## 備註

本文件依《交易系統極限嚴格母表法典》建立，用於明確現行治理基準，避免舊版驗收狀態造成誤解。

**更新記錄**:
- 2026-04-16: 新增候選證據守門機制與驗證腳本
- 2026-04-16: 新增現行正式法典四檔路徑與使用規範
- 2026-04-16: 新增 candidate/merge 前完整重審義務
- 2026-04-16: 新增 03_強化法條版歷史檔案處理規則
- 2026-04-16: 新增 OpenCode 可讀版（readable/）鏡像目錄，明確可讀版為輔助性質，不得取代正式法典

---

*最後更新: 2026-04-16*  
*法源版本: 交易系統極限嚴格母表法典*  
*法典入口: `_governance/law/00_入口與使用規則/00_README.md`*
