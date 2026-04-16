# Evidence Package Template
# 證據包固定回報模板
# 每次任務完成後必須依此格式回報

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

## Validation Result

使用驗證腳本確認：

```powershell
.\scripts\validation\validate_evidence.ps1 -CandidateId "{id}"
```

### 驗證結果
- **status**: {PASS/FAIL}
- **can_mark_candidate_ready**: {true/false}
- **missing_evidence**: 
  - {若有缺失，列於此處}

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
