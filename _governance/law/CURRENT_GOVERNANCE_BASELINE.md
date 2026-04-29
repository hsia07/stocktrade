# CURRENT_GOVERNANCE_BASELINE（當前治理基準）

## 更新日期
2026-04-29

## 當前正式法源優先序（嚴密封閉，不得逆轉）

**第一順位**：02_交易系統極限嚴格母表法典  
**第二順位**：03_161輪逐輪施行細則法典_整合法條增補版  
**第三順位**：04_交易系統法典補強版_20260416_修正版  
**第四順位**：01_系統白話總覽與功能說明  

> ⚠️ **重要**：04 修正版**不是** 01–03 的完整替代，僅是對原 04《交易系統法典補強版_20260416》的修正與擴寫。凡發生衝突，一律採『較嚴格、較不可繞過、較可驗收、較可追責』之解釋。

## 現存治理補丁已落地項（已完成）

- [x] `.githooks/pre-commit` - canonical direct commit guard（阻止單親提交到 canonical）
- [x] `.githooks/pre-push` - canonical direct push guard（阻止未授權推送）
- [x] `automation/control/evidence_checker.py` - evidence validator（證據完整性檢查）
- [x] `_governance/audit/canonical_guard_specification.md` - canonical guard 規格
- [x] `_governance/audit/merge_pre_evidence_gate.md` - merge 前證據閘門規格
- [x] `_governance/audit/global_fail_rules.md` - 7 條全域 FAIL/BLOCK 規則
- [x] `_governance/audit/round_patch_mapping.md` - 14 個 round groups + 算式治理補丁

## 0416 整合法典仍未完成之缺口摘要

### 缺口 1：evidence_checker.py 尚未添加 Law 04 compliance check
- **現狀**：evidence_checker.py 已存在，但尚未檢查 `law_compliance: "04"`
- **要求**：04 修正版第 260 條規定 `automation/control/evidence_checker.py` 必須添加 Law 04 compliance check
- **影響**：無法驗證 candidate 是否符合 Law 04
- **預計完成階段**：Phase 2

### 缺口 2：所有輪次尚未逐輪法條補正
- **現狀**：round_patch_mapping.md 已建立 14 個 round groups，但各輪尚未逐輪對照 04 修正版補正
- **要求**：04 修正版第 251 條規定「All rounds need 逐輪法條補正 to fully align with Law 04」
- **影響**：輪次執行可能未完全符合 Law 04 要求
- **預計完成階段**：Phase 2（配合各輪 candidate/review/merge）

### 缺口 3：candidate pre-review + merge + post-merge repo 全量審計尚未完成
- **現狀**：04 修正版第 250 條要求「Requires: candidate pre-review + merge + post-merge repo full audit」
- **要求**：尚未建立自動化全量審計腳本
- **影響**：無法在 merge 前自動驗證整個 repo 是否符合 Law 04
- **預計完成階段**：Phase 3

### 缺口 4：各 candidate evidence.json 尚未強制包含 `law_compliance: "04"`
- **現狀**：現有 evidence package 尚未強制要求 `law_compliance: "04"`
- **要求**：04 修正版第 261 條規定「Each candidate evidence.json must include `law_compliance: "04"`」
- **影響**：無法追溯 candidate 是否符合 Law 04
- **預計完成階段**：Phase 2（evidence_checker.py 增強）

### 缺口 5：Merge-decision ready 條件尚未綁定 Law 04 compliance verified
- **現狀**：round_patch_mapping.md 第 262 條規定「Merge-decision ready only when Law 04 compliance verified」
- **要求**：尚未在 pre-push hook 或獨立 validator 中實作此檢查
- **影響**：可能 merge 尚未完全符合 Law 04 的 candidate
- **預計完成階段**：Phase 2/3

### 缺口 6：readable/ 鏡像與正式 DOCX 尚未建立自動同步驗證
- **現狀**：readable/ 目錄存在 Markdown 鏡像，但尚未建立自動同步驗證機制
- **要求**：確保 readable/ 與正式 DOCX/MD 內容一致
- **影響**：若 readable/ 與正式版有衝突，可能導致錯誤解釋
- **預計完成階段**：Phase 3

### 缺口 7：pre-push hook 尚未檢查 merge 簽字證據
- **現狀**：pre-push hook 檢查 merge commit 格式，但尚未檢查 04 修正版第 34-37 條規定的簽字證據
- **要求**：merge 前必須取得使用者明示簽字同意
- **影響**：可能未經授權執行 merge
- **預計完成階段**：Phase 2

### 缺口 8：governance drift 自動化檢查尚未完全落地
- **現狀**：04 修正版第 67-75 條已定義 governance drift 檢查規則，但尚未完全自動化
- **要求**：必須以可重跑之 hook 或驗證腳本落地
- **影響**：單輪 branch 可能污染治理檔
- **預計完成階段**：Phase 2/3

## 後續 Phase 2 / Phase 3 施工方向摘要

### Phase 2：02/03/04 逐段吸收（預計施工項目）

1. **evidence_checker.py 增強**
   - 添加 Law 04 compliance check（`law_compliance: "04"`）
   - 添加整輪法條對照檢查（對照 03 施行細則 + 04 修正版）
   - 添加 governance drift 檢查（第 67-75 條）

2. **pre-push hook 增強**
   - 檢查 merge commit 是否包含 Law 04 簽字證據
   - 檢查 `law_compliance: "04"` 是否存在於 evidence.json

3. **candidate 前整輪重檢落點**
   - 在 evidence_checker.py 添加整輪法條對照檢查
   - 確保 candidate 判定時完全符合 04 修正版第 23-28 條

4. **逐輪法條補正**
   - 配合各輪 candidate/review/merge 流程
   - 逐輪對照 04 修正版補正法條

### Phase 3：readable mirror / validator 對齊（預計施工項目）

1. **readable/ 鏡像自動同步驗證**
   - 新增腳本檢查 readable/ 與正式 DOCX/MD 一致性
   - 在 pre-commit 或 CI 中自動執行

2. **merge 前 repo 全量重審自動化**
   - 新增獨立 validator 腳本
   - 實作 04 修正版第 29-33 條規定的 merge 前完整重審

3. **governance drift 完全自動化**
   - 實作 04 修正版第 67-75 條規定的 governance drift 檢查
   - 整合到 pre-push hook 或獨立 validator

4. **RETURN_TO_CHATGPT 輸出驗證**
   - 確保所有輸出完全符合 04 修正版第 38-43 條規定
   - 添加自動化驗證腳本

## 法源衝突處理原則

凡發生衝突，一律採『**較嚴格、較不可繞過、較可驗收、較可追責、較不利於自動化擴權**』之解釋。

具體而言：
1. 若 04 修正版與 02 母表衝突 → 以 **02** 為準
2. 若 04 修正版與 03 施行細則衝突 → 以 **03** 為準
3. 若 03 施行細則與 02 母表衝突 → 以 **02** 為準
4. 若 01 白話總覽與任何正式法源衝突 → 以 **正式法源**（02/03/04）為準
5. 若 readable/ 鏡像與正式版（DOCX/MD）衝突 → 以 **正式版**為準

## 相關文件

- `_governance/law/README.md` - 交易系統法典入口索引
- `_governance/law/00_入口與使用規則/01_法典優先順序.md` - 法源優先序詳細說明
- `_governance/law/00_入口與使用規則/02_OpenCode讀取順序.md` - OpenCode 讀取法源順序
- `_governance/law/04_交易系統法典補強版_20260416_修正版.md` - 第三順位法源
- `_governance/audit/round_patch_mapping.md` - Round patch mapping（含 Law 04 整合缺口說明）
