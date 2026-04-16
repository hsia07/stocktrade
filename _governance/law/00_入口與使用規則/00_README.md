# 現行正式法典入口與使用規則

## 本目錄用途

本目錄 `_governance/law/` 為 stocktrade 交易系統之**現行正式法典**存放處，供 OpenCode、自動流程、人工審核統一讀取。

所有涉及輪次判定、candidate 驗收、merge 決策、治理爭議解決，皆應以本目錄內正式法典為最終依據。

---

## 現行正式法典四檔清單

| 序號 | 檔名 | 性質 | 說明 |
|------|------|------|------|
| 01 | `01_系統白話總覽與功能說明.docx` | 白話導覽 | 輔助理解、快速入門，**不得作為正式輪次判定依據** |
| 02 | `02_交易系統極限嚴格母表法典.docx` | 母表硬法 | 最高位階之全域硬規則 |
| 03 | `03_161輪逐輪施行細則法典_整合法條增補版.docx` | 逐輪施行細則 | 每輪具體條文、驗收標準、交付要求 |
| 04 | `04_交易系統法典補強版_20260416_修正版.md` | 補強版 | 補強 02/03 未明載之治理規則，**不得取代 02/03** |

---

## 法典位階說明

### 02 - 母表硬法
- **地位**：最高優先
- **內容**：交易系統極限嚴格母表法典
- **用途**：全域性、跨輪次、不可繞過之硬規則
- **OpenCode 注意**：不得只看白話總覽（01）就做正式輪次判定，必須回歸母表硬法（02）

### 03 - 逐輪施行細則
- **地位**：次於母表，高於補強版與白話總覽
- **內容**：161 輪逐輪施行細則法典（整合法條增補版）
- **用途**：單輪具體條文、驗收標準、交付物清單
- **OpenCode 注意**：判單輪是否 candidate / 是否 merge 時，必須回讀該輪在 03 中之完整條文

### 04 - 補強版
- **地位**：補充性質，不取代 02/03
- **內容**：交易系統法典補強版 2026-04-16 修正版
- **用途**：補強 02/03 未明載之治理規則（如：證據包格式、validate_evidence.ps1 規則）
- **衝突處理**：若與 02/03 衝突，以 02/03 為準

### 01 - 白話總覽
- **地位**：輔助文件，最低位階
- **內容**：系統白話總覽與功能說明
- **用途**：快速理解系統架構，新人入門參考
- **警告**：**OpenCode 不得以此作為正式輪次判定依據**

---

## 快速導航

- [法典優先順序](./01_法典優先順序.md)
- [OpenCode 讀取順序](./02_OpenCode讀取順序.md)

---

## 歷史檔案

- `03_161輪逐輪施行細則法典_強化法條版.docx`（若存在）：僅作歷史底稿，非現行正式法典

---

## OpenCode 可讀版（鏡像）

### 可讀版目錄

為便利 OpenCode / 自動審核流程，現行正式法典四檔已轉換為機器可讀之 Markdown 格式，存放於：

**`_governance/law/readable/`**

### 可讀版檔案清單

| 檔名 | 說明 |
|------|------|
| `01_系統白話總覽與功能說明.md` | 白話導覽可讀版 |
| `02_交易系統極限嚴格母表法典.md` | 母表硬法可讀版 |
| `03_161輪逐輪施行細則法典_整合法條增補版.md` | 逐輪施行細則可讀版 |
| `03_R7-R9_正式審核可讀節錄.md` | R7-R9 單輪審核用節錄 |
| `04_交易系統法典補強版_20260416_修正版.md` | 補強版可讀版 |

### 可讀版使用規則

⚠️ **重要聲明**：

1. **正式法源仍以現行正式四檔為準**（.docx / .md 原始檔）
2. **可讀版僅為機器可讀鏡像**，不得視為新的獨立法源順位
3. **若可讀版與正式法源有衝突，以正式法源為準**
4. **OpenCode 優先讀取可讀版**，但必須理解其為鏡像性質

### R7-R9 正式審核指引

審核 R-007 / R-008 / R-009 時，優先參閱：
- `_governance/law/readable/03_R7-R9_正式審核可讀節錄.md`

該檔為 03 逐輪施行細則之節錄，專供 R7-R9 正式審核使用。

---

## Phase 級治理與主核心 Merge

### Work Branch 與 Master 之區別

- **work branch**（如 `work/r006-governance`）：Phase 內收口工作主線，供多輪逐步匯集與 Phase 內整合測試
- **master / 主核心分支**：正式發布與生產就緒之獨立保護層

### 單輪收口 vs Phase 級收口

| 階段 | 說明 | 授權層級 |
|------|------|----------|
| 單輪 merge 到 work branch | 該輪在 Phase 工作主線內完成收口 | 單輪級簽字 |
| Phase 級總審核 | Phase 內所有輪次協同驗證 | Phase 級審核 |
| Phase 級主核心 merge | 整個 Phase 進入 master | **需另外明示簽字** |

### OpenCode 執行規則

1. 單輪已 merge 到 work branch **不等於** 可直接進入 master
2. 到達 Phase 級主核心 merge 決策點時，OpenCode **必須停止**並等待使用者明示簽字
3. 未獲使用者明示同意前，不得提供主核心 merge 指令
4. 若 Phase 內仍存在未完成輪次（candidate only / review only / technical_unfinished / blocked），原則上不得進行主核心 merge

---

## Shell / Git 非互動執行規則

### OpenCode 執行 git / shell 任務時

**核心原則**：所有命令列操作必須採非互動模式，不得等待人工輸入。

| 任務類型 | 必須遵循 |
|----------|----------|
| **merge** | 使用 `--no-edit --no-ff` 等非互動參數 |
| **push** | 確認前置檢查完成後執行，超時 15 秒即中止 |
| **switch** | 先驗證分支存在再切換 |
| **verify** | 使用 `--porcelain` 等機器可讀格式 |

### 強制停止條件

- **超時**：超過 15 秒無結果 → 立即停止，回報 technical_unfinished
- **Conflict**：merge conflict → 立即 `git merge --abort`，回報 technical_unfinished
- **失敗**：完整回報 executed_command、stdout、stderr、failure_point

### 禁止事項

- ❌ 打開 editor、pager
- ❌ 等待人工輸入
- ❌ 自行交互式修復衝突
- ❌ 多輪猜測式 shell 嘗試
- ❌ 停在「思考中」無限等待

---

## Governance Drift 檢查與單輪分支管理

### 單輪任務若不是治理修法任務

**原則上不得碰治理檔**：
- ❌ CURRENT_GOVERNANCE_BASELINE.md
- ❌ _governance/law/00_入口與使用規則/**
- ❌ _governance/law/04_交易系統法典補強版_20260416_修正版.md
- ❌ _governance/law/readable/**

### Promote / Merge 前必做 Governance Drift Check

**檢查命令**：
```bash
git diff --name-only <work_branch>...<target_branch>
```

**若輸出治理檔，不得繼續**，必須回報：
- target branch
- base work branch
- drifted governance files
- resolution suggestion

### 建議解決方案

| 方案 | 適用情境 |
|------|----------|
| **rebase onto latest work** | branch 基底落後，但功能內容完整 |
| **replay branch** | 從最新 work branch 重新開出 branch |
| **split governance changes** | 治理檔變更應拆分為獨立治理任務 |

### 新單輪 Branch 開出規則

**必須從最新 work branch 開出**：
```bash
git checkout -b <new_round_branch> work/r006-governance
```

**禁止從落後基底開出**，避免帶入舊版治理文件。

---

*最後更新：2026-04-16*
