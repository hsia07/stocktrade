# 現行治理基準 / CURRENT_GOVERNANCE_BASELINE

## 法源優先順序

1. **交易系統極限嚴格母表法典**（最高優先）
2. **161輪逐輪施行細則法典**（整合法條增補版）
3. **交易系統法典補強版 2026-04-16**
4. **本次任務補充規則**

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

## 候選證據守門機制

### 證據驗證工具
- **腳本**: `scripts/validation/validate_evidence.ps1`
- **用途**: 檢查任務是否產出完整證據包

### Candidate Ready 前提條件

1. **證據包完整**（缺一不可）：
   - `task.txt` - 任務描述文件
   - `aider.log` - Aider 執行日誌
   - `candidate.diff` - 代碼變更 diff
   - `report.json` - 執行報告
   - `git status --short` - Git 狀態
   - `git diff --name-only` - 變更檔案清單

2. **安全開關狀態**：
   - 標準模式：允許未提交更改（WARN）
   - 嚴格模式（-StrictMode）：不允許未提交更改（FAIL）

3. **測試證據**（若本輪有指定）：
   - 測試檔案必須存在
   - 測試必須通過

### 使用方式
```powershell
# 標準驗證
.\scripts\validation\validate_evidence.ps1 -CandidateId "TASK-001"

# 嚴格模式
.\scripts\validation\validate_evidence.ps1 -CandidateId "TASK-001" -StrictMode

# 指定測試證據
.\scripts\validation\validate_evidence.ps1 -CandidateId "TASK-001" -RequiredTests @("tests/test_feature.py")
```

### 驗證結果判定
- **PASS**: 所有必需證據存在，可標記 candidate_ready
- **FAIL**: 缺少必需證據，**不得**標記 candidate_ready

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

## 備註

本文件依《交易系統極限嚴格母表法典》建立，用於明確現行治理基準，避免舊版驗收狀態造成誤解。

**更新記錄**:
- 2026-04-16: 新增候選證據守門機制與驗證腳本

---

*最後更新: 2026-04-16*  
*法源版本: 交易系統極限嚴格母表法典*
