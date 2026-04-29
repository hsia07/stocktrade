# OpenCode 讀取法源順序

## 核心原則

**readable/ 鏡像只能輔助閱讀，不得凌駕正式法源。**

正式法源優先序：02 > 03 > 04 > 01（DOCX/MD 正式版）

## 一般執行時讀取順序

1. **先讀 04_交易系統法典補強版_20260416_修正版.md**（第三順位，跨輪治理補強）
2. **再讀 02_交易系統極限嚴格母表法典.docx**（第一順位，全域硬規則）
3. **再讀 03_161輪逐輪施行細則法典_整合法條增補版.docx**（第二順位，現行操作版）
4. **必要時讀 01_系統白話總覽與功能說明.docx**（第四順位，白話導覽）

> ⚠️ 若 readable/ 鏡像與正式版有衝突，以正式版（DOCX/MD）為準。

## candidate 前整輪重檢讀取順序

當判定某輪是否可提交至 candidate 時，必須：

1. **讀取該輪完整法條**（來自 03_161輪逐輪施行細則法典_整合法條增補版.docx）
2. **讀取 04_交易系統法典補強版_20260416_修正版.md**（第23-28條：候選完整功能判定）
3. **讀取 02_交易系統極限嚴格母表法典.docx**（全域硬規則、直接 FAIL 條件）
4. **逐項檢查該輪要求的所有功能、所有必要契約、所有必要情境與所有直接 FAIL 條件**
5. **不得只看最後修改片段、commit message、單段摘要、單張 diff、單一測試或 AI 口頭回報**

### 整輪重檢檢查清單

- [ ] 該輪唯一主題所有必做功能皆已具備
- [ ] 功能不僅存在，且可正常運行
- [ ] 必要契約與狀態一致
- [ ] 必要測試與驗證通過
- [ ] evidence package 完整
- [ ] hard gate 真正執行且 PASS
- [ ] 無 fabricated evidence
- [ ] 無越權修改

## merge 前 repo 全量重審讀取順序

當候選已進入 candidate_ready_awaiting_manual_review 或 review branch 階段，判定是否可 merge 時，必須：

1. **重新讀取 04_交易系統法典補強版_20260416_修正版.md**（第29-33條：merge 前完整重審義務）
2. **重新讀取該輪完整法條**（來自 03_161輪逐輪施行細則法典_整合法條增補版.docx）
3. **重新讀取 02_交易系統極限嚴格母表法典.docx**（全域硬規則、直接 FAIL 條件）
4. **重新讀取 repo 內與該輪有關之實際檔案、測試、契約、驗收記錄、run record、evidence package**
5. **不得僅依 RETURN_TO_CHATGPT 摘要、candidate 名稱或單段 acceptance 摘要做決策**

### merge 前重審範圍

- [ ] 該輪唯一主題
- [ ] 所有必做功能
- [ ] 所有必要契約
- [ ] 所有必要情境與直接 FAIL 條件
- [ ] 實際 repo 檔案與測試
- [ ] candidate / review branch 差異
- [ ] hard gate 是否真實通過
- [ ] 是否仍存在未解決風險
- [ ] Law 04 compliance 檢查（evidence.json 包含 `law_compliance: "04"`）

## readable/ 鏡像使用規則

### 允許用途
- ✅ 快速查找法條
- ✅ 輔助理解（配合正式版）
- ✅ OpenCode/Aider 快速讀取（當內容與正式版一致時）

### 禁止用途
- ❌ 作為正式法源依據（當與正式版有衝突時）
- ❌ 凌駕 02/03/04 正式版
- ❌ 單獨作為 candidate 判定或 merge 決策的唯一依據

### 同步要求
- readable/ 內容應與正式版保持一致
- 尚未建立自動同步驗證機制（參見 CURRENT_GOVERNANCE_BASELINE.md）
- 若有疑義，以正式版（DOCX/MD）為準

## 緊急情境讀取順序

當遇到 governance drift、merge conflict、或違規操作時：

1. **先讀 04_交易系統法典補強版_20260416_修正版.md**（第59-75條：Shell/Git 非互動執行、Governance Drift 治理）
2. **再讀 .githooks/pre-commit 與 .githooks/pre-push**（canonical guard 實作）
3. **再讀 _governance/audit/ 相關文件**（canonical_guard_specification.md、merge_pre_evidence_gate.md 等）

## 相關文件

- `../README.md` - 交易系統法典入口索引
- `01_法典優先順序.md` - 法源優先序詳細說明
- `../../CURRENT_GOVERNANCE_BASELINE.md` - 當前治理基準
- `../../04_交易系統法典補強版_20260416_修正版.md` - 第三順位法源（含詳細讀取指示）
