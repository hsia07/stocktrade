# 交易系統法典入口索引

## 法源優先順序（嚴密封閉，不得逆轉）

**第一順位**：02_交易系統極限嚴格母表法典  
**第二順位**：03_161輪逐輪施行細則法典_整合法條增補版  
**第三順位**：04_交易系統法典補強版_20260416_修正版  
**第四順位**：01_系統白話總覽與功能說明  

> ⚠️ **重要**：04 修正版**不是** 01–03 的完整替代，僅是對原 04《交易系統法典補強版_20260416》的修正與擴寫。凡發生衝突，一律採『較嚴格、較不可繞過、較可驗收、較可追責』之解釋。

## 文件結構

```
_governance/law/
├── README.md                          # 本文件：主索引與法源優先順序
├── 00_入口與使用規則/                 # 入口規則與讀取順序
│   ├── 01_法典優先順序.md            # 法源優先序詳細說明
│   └── 02_OpenCode讀取順序.md       # OpenCode 讀取法源順序
├── 01_系統白話總覽與功能說明.docx    # 第四順位：白話導覽（不得推翻 02/03/04）
├── 02_交易系統極限嚴格母表法典.docx  # 第一順位：全域硬規則、證據規則、直接 FAIL 條件
├── 03_161輪逐輪施行細則法典_整合法條增補版.docx  # 第二順位：161 輪具體施行條文
├── 04_交易系統法典補強版_20260416_修正版.md     # 第三順位：跨輪治理補強（修正版）
├── 161輪正式重編主題總表_唯一基準版_v2.md
├── readable/                          # 可讀鏡像（輔助閱讀，不得凌駕正式法源）
│   ├── 01_系統白話總覽與功能說明.md
│   ├── 02_交易系統極限嚴格母表法典.md
│   ├── 03_161輪逐輪施行細則法典_整合法條增補版.md
│   └── 04_交易系統法典補強版_20260416_修正版.md
├── archive/                           # 歷史版本（追溯參照用）
└── CURRENT_GOVERNANCE_BASELINE.md    # 當前治理基準（動態更新）
```

## 各文件定位

### 01_系統白話總覽與功能說明（第四順位）
- **定位**：白話導覽與能力結構說明文件
- **用途**：協助理解 Phase、系統定位與風險區
- **限制**：不得推翻 02、03 或 04 正文；僅供輔助理解

### 02_交易系統極限嚴格母表法典（第一順位）
- **定位**：全域硬規則、證據規則、固定模板義務、直接 FAIL 條件與輪次法條模板之總法
- **用途**：所有輪次執行的首要依據
- **格式**：DOCX（正式版）+ readable/ Markdown 鏡像（輔助閱讀）

### 03_161輪逐輪施行細則法典_整合法條增補版（第二順位）
- **定位**：現行輪次操作版，負責每輪唯一主題、必做實作、成功/失敗/邊界/恢復/非法情境、直接 FAIL 條件與通過標準
- **用途**：單輪 candidate、review、merge 控制的具體依據
- **格式**：DOCX（正式版）+ readable/ Markdown 鏡像（輔助閱讀）

### 04_交易系統法典補強版_20260416_修正版（第三順位）
- **定位**：原 04《交易系統法典補強版_20260416》之修正版與擴寫版，負責處理主線/側線、OpenCode 角色、候選證據、merge 簽字、多輪候選預製、RETURN_TO_CHATGPT 主體輸出、Phase 授權等跨輪治理補強條文
- **用途**：跨輪治理、候選、merge、授權與 Phase 自動化情境的補強依據
- **格式**：Markdown（可直接被 OpenCode 讀取）
- **重要**：本文件**不是** 01–03 的完整替代，僅是對原 04 的修正與擴寫

## readable/ 目錄定位

- **用途**：提供 Markdown 可讀鏡像，供 OpenCode、Aider、驗收腳本快速讀取
- **限制**：**不得凌駕正式法源**（DOCX 版本）；若 readable/ 與正式版有衝突，以正式版為準
- **同步要求**：readable/ 內容應與正式版保持一致，但尚未建立自動同步驗證機制（參見 CURRENT_GOVERNANCE_BASELINE.md）

## archive/ 目錄定位

- **用途**：存放歷史版本（如 03_161輪逐輪施行細則法典_強化法條版），供法意追溯與比對
- **限制**：archive/ 內文件不作現行操作依據

## OpenCode 讀取順序

詳見 `00_入口與使用規則/02_OpenCode讀取順序.md`

## 法源衝突處理

凡發生衝突，一律採『**較嚴格、較不可繞過、較可驗收、較可追責、較不利於自動化擴權**』之解釋。

## 現行治理補丁（已落地）

- [x] `.githooks/pre-commit` - canonical direct commit guard
- [x] `.githooks/pre-push` - canonical direct push guard
- [x] `automation/control/evidence_checker.py` - evidence validator
- [x] `_governance/audit/canonical_guard_specification.md`
- [x] `_governance/audit/merge_pre_evidence_gate.md`
- [x] `_governance/audit/global_fail_rules.md`
- [x] `_governance/audit/round_patch_mapping.md`

## 0416 整合法典整合缺口（尚未完成）

詳見 `CURRENT_GOVERNANCE_BASELINE.md`

## 相關文件

- `00_入口與使用規則/01_法典優先順序.md` - 法源優先序詳細說明
- `00_入口與使用規則/02_OpenCode讀取順序.md` - OpenCode 讀取法源順序
- `CURRENT_GOVERNANCE_BASELINE.md` - 當前治理基準與缺口摘要
- `_governance/audit/` - 治理審計文件（canonical guard、evidence gate、global fail rules、round patch mapping）
