# Evidence Package Template
# 證據包固定回報模板
# ⚠️ 硬規則：未執行 validate_evidence.ps1 並通過，不得標記 candidate_ready
# ⚠️ 硬規則：validate_evidence.ps1 失敗時，只能回報 technical_unfinished / blocked

---

## Evidence Package

- **candidate_id**: {填入 CAND-XXX-001 格式 ID}
- **candidate_branch**: {填入 candidates/XXX-001 格式分支名}
- **commit_hash**: {填入 commit hash 前 7 碼}

---

## Required Files Check

| 檔案 | 狀態 | 備註 |
|------|------|------|
| task.txt | ⬜ / ✅ | 任務描述 |
| aider.log | ⬜ / ✅ | Aider 執行日誌 |
| candidate.diff | ⬜ / ✅ | 代碼變更 diff |
| report.json | ⬜ / ✅ | 執行報告 |

---

## Git Status

```
{在此貼上 git status --short 輸出}
```

### 變更摘要
- **modified_files**: {數量}
- **untracked_files**: {數量}
- **working_tree_clean**: {yes/no}

---

## Test Evidence

| 測試檔案 | 狀態 | 通過數 |
|----------|------|--------|
| {test_file_1} | ⬜ / ✅ | {pass}/{total} |
| {test_file_2} | ⬜ / ✅ | {pass}/{total} |

---

## Validation Result (HARD GATE ⚠️)

**⚠️ 硬規則：本區塊為 candidate_ready 的硬門檻，未通過不得標記完成**

### 執行驗證
```powershell
.\scripts\validation\validate_evidence.ps1 -CandidateId "{id}"
```

### 驗證結果
- **executed**: {yes/no - 若為 no，立即判定不合格}
- **status**: {PASS/FAIL}
- **can_mark_candidate_ready**: {true/false}
- **formal_status_code**: 
  - 若 PASS: `candidate_ready_eligible`
  - 若 FAIL: `technical_unfinished` 或 `blocked`
- **missing_evidence**: 
  - {若有缺失，列於此處}

### 判定結果
- [ ] **驗證未執行** → 不得回報 candidate_ready
- [ ] **驗證 FAIL** → 回報 technical_unfinished / blocked
- [ ] **驗證 PASS** → 可回報 candidate_ready

---

## Evidence Level Classification

| 證據項目 | 等級 | 狀態 |
|----------|------|------|
| pytest 測試結果 | 一級 | ⬜ |
| API response | 一級 | ⬜ |
| state snapshot | 一級 | ⬜ |
| 不可變事件 log | 一級 | ⬜ |
| diff | 二級 | ⬜ |
| schema/contract | 二級 | ⬜ |
| regression report | 二級 | ⬜ |
| UI 截圖 | 三級 | ⬜ |
| 人工清單 | 三級 | ⬜ |

---

## Sign-off

- **驗證執行人**: {name}
- **驗證時間**: {timestamp}
- **candidate_ready 判定**: {YES/NO}

---

*本模板依 CURRENT_GOVERNANCE_BASELINE.md 證據守門機制建立*
