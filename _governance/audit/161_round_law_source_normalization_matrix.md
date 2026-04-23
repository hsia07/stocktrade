# 161 輪法源主題校正矩陣

**校正輪次**: GOV-161-ROUND-LAW-SOURCE-NORMALIZATION
**校正日期**: 2026-04-23
**校正依據**: 03_161輪逐輪施行細則法典（整合法條增補版）+ 161輪正式重編主題總表（唯一主題基準版）

**總輪次**: 161
**不一致輪次**: 155
**一致輪次**: 6
**需修正輪次**: 155

---

## 逐輪校正詳細矩陣

| 輪次 | Phase | 舊主題 (v2.0) | 正確主題 (v2.1) | 是否一致 | 風險等級 | 風險說明 |
|------|-------|---------------|-----------------|----------|----------|----------|
| R001 | Phase 1 | 基礎治理入口與執行邊界建立 | 穩定性 / 一致性 / restore / validate / 設定同步 | ❌ | HIGH | Phase 1 topic mismatch affects closure declaration and governance references |
| R002 | Phase 1 | 啟動/停止/暫停控制基底 | 網站掛掉風險清單 + 防呆機制 | ❌ | HIGH | Phase 1 topic mismatch affects closure declaration and governance references |
| R003 | Phase 1 | 狀態檔與持久化基底 | 單一真實來源 | ❌ | HIGH | Phase 1 topic mismatch affects closure declaration and governance references |
| R004 | Phase 1 | 候選、證據、回報骨架 | 時間同步與時序一致性 | ❌ | HIGH | Phase 1 topic mismatch affects closure declaration and governance references |
| R005 | Phase 1 | 歷史歸檔與可追溯鏈銜接 | 版本一致性與決策快照 | ❌ | HIGH | Phase 1 topic mismatch affects closure declaration and governance references |
| R006 | Phase 1 | 控制面板完整功能落地 | 健康檢查 / 熔斷 / 降級中心 | ❌ | HIGH | Phase 1 topic mismatch affects closure declaration and governance references |
| R007 | Phase 1 | 異常靜默保護 | 異常靜默保護 | ✅ | NONE | No change needed |
| R008 | Phase 1 | 狀態機與模式切換治理 | 狀態機與模式切換治理 | ✅ | NONE | No change needed |
| R009 | Phase 1 | 指令與任務優先級 | 指令與任務優先級 | ✅ | NONE | No change needed |
| R010 | Phase 1 | 啟動鏈、bridge、wrapper、actual command 對齊 | 核心與非核心隔離 | ❌ | HIGH | Phase 1 topic mismatch affects closure declaration and governance references |
| R011 | Phase 1 | artifact、report、latest/history 產物完整化 | 效能與載入架構優化 | ❌ | HIGH | Phase 1 topic mismatch affects closure declaration and governance references |
| R012 | Phase 1 | 決策延遲預算/AI 超時降級機制 | 決策延遲預算 / AI 超時降級機制 | ❌ | LOW | Topic unchanged, no governance impact |
| R013 | Phase 1 | 實時與歷史資料分離 | 實時與歷史資料分離 | ✅ | NONE | No change needed |
| R014 | Phase 1 | 可觀測性統一格式 | 可觀測性統一格式 | ✅ | NONE | No change needed |
| R015 | Phase 1 | 多層快取策略 | 多層快取策略 | ✅ | NONE | No change needed |
| R016 | Phase 1 | 決策來源追溯與主張者紀錄 | 欄位命名 / API schema / 資料契約固定 | ❌ | CRITICAL | Frozen infrastructure built on wrong topic; requires re-qualification |
| R017 | Phase 2 | 風控前置檢查與阻擋 | 秘密與金鑰管理 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R018 | Phase 2 | 下單意圖序列化 | 資料遷移與 schema 升級機制 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R019 | Phase 2 | 委託前驗證與白名單 | SLO / 延遲預算 / 穩定目標 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R020 | Phase 2 | 部位/曝險/資金佔用計算 | 使用者誤操作保護 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R021 | Phase 2 | 停損停利與熔斷中斷 | 重要設定鎖定 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R022 | Phase 2 | 斷線/API失敗 fallback | 新手可理解化 / 教學式 UI | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R023 | Phase 2 | 委託狀態一致性與回寫 | 首頁與新手操作體驗強化 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R024 | Phase 2 | 訂單/成交/持倉三表一致 | 智慧摘要層 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R025 | Phase 2 | 日誌可追責鏈補全 | 手機友善 / 行動版 / 緊急接管介面 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R026 | Phase 2 | 滑價與流動性保守估算 | 模擬交易介面重構 / 真實感升級 / 新手友善化 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R027 | Phase 2 | 漲跌停 ±10% 規則映射 | 開盤 / 收盤保護機制 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R028 | Phase 2 | T+2 交割限制映射 | 交易生命週期 / execution / outcome / review | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R029 | Phase 2 | 競價撮合節奏與可成交性 | 六大 AI 決策會議可視化 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R030 | Phase 2 | 價格/數量合法性檢查 | 決策前檢查清單 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R031 | Phase 2 | 重啟後持倉還原 | 信心來源拆解 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R032 | Phase 2 | 重啟後訂單還原 | 交易日誌可追責鏈 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R033 | Phase 2 | 重啟後風控狀態還原 | 交易回放與決策前後對照 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R034 | Phase 2 | 影子下單/模擬執行一致性 | 回放與真實模式隔離 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R035 | Phase 2 | 交易中斷後恢復策略 | 快速驗證與壓力測試框架 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R036 | Phase 2 | 例外分類與分級停機 | 固定測試資料集 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R037 | Phase 2 | 人工介入點與覆核 | 自動回歸檢查 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R038 | Phase 2 | 盤中時間窗限制 | 策略 CI/CD 驗證鏈 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R039 | Phase 2 | 多來源行情一致性檢查 | 資料標註與人工審閱工具 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R040 | Phase 2 | 行情遲延與陳舊資料阻擋 | 全市場候選池與任意股票查詢 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R041 | Phase 2 | 主張→否決→最終成交鏈 | features / regimes / strategies | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R042 | Phase 2 | 損益歸因與事後檢討 | 股票池分層治理 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R043 | Phase 2 | 警報/通知/升級鏈 | 新聞 / 事件分析層 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R044 | Phase 2 | 候選前台股規則總檢 | 事件去重與舊聞污染保護 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R045 | Phase 2 | Phase 2 尾輪補遺與總封箱 | 事件重要度分層與壽命管理 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R046 | Phase 2 | Phase 2 特別補遺輪 | 事件衝突整合器 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R047 | Phase 2 | Phase 2 特別補遺輪（45A） | execution / slippage / liquidity / sizing / 強風控 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R048 | Phase 2 | Phase 2 特別補遺輪（45A） | 市場微觀結構基礎引擎 | ❌ | MEDIUM | Phase 2 topic mismatch affects future round planning |
| R049 | Phase 3 | NOT_IN_OLD_V2 | 成交真實度模擬升級 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R050 | Phase 3 | NOT_IN_OLD_V2 | 真實淨損益計算 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R051 | Phase 3 | NOT_IN_OLD_V2 | 風險預算可視化 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R052 | Phase 3 | NOT_IN_OLD_V2 | 低虧損核心 / 超強風控 / No-Trade 機制 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R053 | Phase 3 | NOT_IN_OLD_V2 | 部位與風險硬上限保險絲 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R054 | Phase 3 | NOT_IN_OLD_V2 | 資料品質稽核層 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R055 | Phase 3 | NOT_IN_OLD_V2 | 容量管理 / 記憶體與儲存優化 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R056 | Phase 3 | NOT_IN_OLD_V2 | 自動封存與安全清理機制 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R057 | Phase 3 | NOT_IN_OLD_V2 | 週月複盤 / walk-forward / 策略淘汰 / 健康度 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R058 | Phase 3 | NOT_IN_OLD_V2 | 成功 / 失敗定義標準化 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R059 | Phase 3 | NOT_IN_OLD_V2 | 系統自我診斷報告 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R060 | Phase 3 | NOT_IN_OLD_V2 | 交易後學習品質分層 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R061 | Phase 3 | NOT_IN_OLD_V2 | 反事實分析 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R062 | Phase 3 | NOT_IN_OLD_V2 | 誤報與漏報分析 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R063 | Phase 3 | NOT_IN_OLD_V2 | 學習資料品質評估 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R064 | Phase 3 | NOT_IN_OLD_V2 | 樣本污染與倖存者偏差防護 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R065 | Phase 3 | NOT_IN_OLD_V2 | 權重更新節流 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R066 | Phase 3 | NOT_IN_OLD_V2 | 學習停手機制 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R067 | Phase 3 | NOT_IN_OLD_V2 | 學習回滾機制 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R068 | Phase 3 | NOT_IN_OLD_V2 | 多時間框架 / 市場上下文資料層 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R069 | Phase 3 | NOT_IN_OLD_V2 | 市場地圖 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R070 | Phase 3 | NOT_IN_OLD_V2 | portfolio / 曝險 / 組合風控 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R071 | Phase 3 | NOT_IN_OLD_V2 | 組合再平衡機制 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R072 | Phase 3 | NOT_IN_OLD_V2 | 自動股票輪動與優先級切換 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R073 | Phase 3 | NOT_IN_OLD_V2 | 候選股培養機制 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R074 | Phase 3 | NOT_IN_OLD_V2 | 決策穩定度監控 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R075 | Phase 3 | NOT_IN_OLD_V2 | 組合關聯風險網路 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R076 | Phase 3 | NOT_IN_OLD_V2 | 觀察名單智慧化 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R077 | Phase 3 | NOT_IN_OLD_V2 | 研究平台 / 壓力測試 / robustness / attribution | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R078 | Phase 3 | NOT_IN_OLD_V2 | 交易成本總帳 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R079 | Phase 3 | NOT_IN_OLD_V2 | 實驗追蹤中心 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R080 | Phase 3 | NOT_IN_OLD_V2 | 研究結論驗證關卡 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R081 | Phase 3 | NOT_IN_OLD_V2 | 治理 / 版本 / 審計 / rollback | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R082 | Phase 3 | NOT_IN_OLD_V2 | 政策與規則變更追蹤 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R083 | Phase 3 | NOT_IN_OLD_V2 | 規則衝突檢查器 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R084 | Phase 3 | NOT_IN_OLD_V2 | LLM 研究助理接口 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R085 | Phase 3 | NOT_IN_OLD_V2 | 策略失效偵測 / 自動研究待辦 / 自我評分 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R086 | Phase 3 | NOT_IN_OLD_V2 | 部件健康度儀表 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R087 | Phase 3 | NOT_IN_OLD_V2 | 股票人格檔案 / 個股行為模型 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R088 | Phase 3 | NOT_IN_OLD_V2 | 因子 / 特徵淘汰機制 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R089 | Phase 3 | NOT_IN_OLD_V2 | 策略與股票配對矩陣 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R090 | Phase 3 | NOT_IN_OLD_V2 | 個股生命週期管理 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R091 | Phase 3 | NOT_IN_OLD_V2 | 影子模式 / 安全上線 / 多層風險開關 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R092 | Phase 3 | NOT_IN_OLD_V2 | 重大操作模擬預演 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R093 | Phase 3 | NOT_IN_OLD_V2 | 重大異常後恢復觀察期 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R094 | Phase 3 | NOT_IN_OLD_V2 | 恢復期階梯式冷啟動授權 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R095 | Phase 3 | NOT_IN_OLD_V2 | 人工接管與多層暫停 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R096 | Phase 3 | NOT_IN_OLD_V2 | 最終人工保險絲 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R097 | Phase 3 | NOT_IN_OLD_V2 | 備份 / 快照 / 回滾保護 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R098 | Phase 3 | NOT_IN_OLD_V2 | 實盤準備 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R099 | Phase 3 | NOT_IN_OLD_V2 | 零股驗證 / 成交累積模式 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R100 | Phase 3 | NOT_IN_OLD_V2 | 冷啟動策略 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R101 | Phase 3 | NOT_IN_OLD_V2 | 不同模式不同 KPI | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R102 | Phase 3 | NOT_IN_OLD_V2 | 富邦 Neo API 專用接入架構 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R103 | Phase 3 | NOT_IN_OLD_V2 | 模擬資金與盤前/盤中自動模擬交易 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R104 | Phase 3 | NOT_IN_OLD_V2 | 富邦配額保護與訂閱池管理 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R105 | Phase 3 | NOT_IN_OLD_V2 | Tick 訂閱池預排與盤中動態替換 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R106 | Phase 3 | NOT_IN_OLD_V2 | 當沖資金保護 / 最壞情境交割能力檢查 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R107 | Phase 3 | NOT_IN_OLD_V2 | 盤前模擬沙盤 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R108 | Phase 3 | NOT_IN_OLD_V2 | 盤中節奏控制 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R109 | Phase 3 | NOT_IN_OLD_V2 | 市場制度 / 規則引擎 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R110 | Phase 3 | NOT_IN_OLD_V2 | 多層回測模式 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R111 | Phase 3 | NOT_IN_OLD_V2 | 依賴替身模式 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R112 | Phase 3 | NOT_IN_OLD_V2 | shadow 與小資金 live | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R113 | Phase 3 | NOT_IN_OLD_V2 | 真實 vs 模擬偏差追蹤 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R114 | Phase 3 | NOT_IN_OLD_V2 | 正式 live gating | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R115 | Phase 3 | NOT_IN_OLD_V2 | 券商回報對帳中心 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R116 | Phase 3 | NOT_IN_OLD_V2 | 故障演練與災難恢復演習 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R117 | Phase 3 | NOT_IN_OLD_V2 | 實盤監控中心 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R118 | Phase 3 | NOT_IN_OLD_V2 | 實盤事故中心 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R119 | Phase 3 | NOT_IN_OLD_V2 | 總指揮中心收斂版 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R120 | Phase 3 | NOT_IN_OLD_V2 | 比較與評估中心 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R121 | Phase 3 | NOT_IN_OLD_V2 | 信心校準與衝突管理 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R122 | Phase 3 | NOT_IN_OLD_V2 | 全局決策品質評分 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R123 | Phase 3 | NOT_IN_OLD_V2 | 反脆弱與極端市場保護 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R124 | Phase 3 | NOT_IN_OLD_V2 | AI 治理中心 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R125 | Phase 3 | NOT_IN_OLD_V2 | 元控制器 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R126 | Phase 3 | NOT_IN_OLD_V2 | 任務中心與自動研究排程 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R127 | Phase 3 | NOT_IN_OLD_V2 | 個人化工作流 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R128 | Phase 3 | NOT_IN_OLD_V2 | 自動待辦與欠債清單 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R129 | Phase 3 | NOT_IN_OLD_V2 | 研究工廠 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R130 | Phase 3 | NOT_IN_OLD_V2 | 策略工廠強化 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R131 | Phase 3 | NOT_IN_OLD_V2 | 研究筆記自動化 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R132 | Phase 3 | NOT_IN_OLD_V2 | 資料與功能淘汰機制 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R133 | Phase 4 | NOT_IN_OLD_V2 | 多帳戶與營運化 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R134 | Phase 4 | NOT_IN_OLD_V2 | 正式環境發版隔離與灰度發布 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R135 | Phase 4 | NOT_IN_OLD_V2 | 配置檔環境分離 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R136 | Phase 4 | NOT_IN_OLD_V2 | 自適應市場模式 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R137 | Phase 4 | NOT_IN_OLD_V2 | 知識庫與學習節奏控制 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R138 | Phase 4 | NOT_IN_OLD_V2 | 人機協作與授權層 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R139 | Phase 4 | NOT_IN_OLD_V2 | 權限最小化 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R140 | Phase 4 | NOT_IN_OLD_V2 | 核心目標管理器 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R141 | Phase 4 | NOT_IN_OLD_V2 | 長期人格與目標管理 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R142 | Phase 4 | NOT_IN_OLD_V2 | 使用者風格與解釋品質升級 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R143 | Phase 4 | NOT_IN_OLD_V2 | 模式切換細化 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R144 | Phase 4 | NOT_IN_OLD_V2 | 使用痕跡與操作記錄 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R145 | Phase 4 | NOT_IN_OLD_V2 | 可解釋性評分 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R146 | Phase 4 | NOT_IN_OLD_V2 | 使用者偏好學習 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R147 | Phase 4 | NOT_IN_OLD_V2 | 交易心理模擬層 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R148 | Phase 4 | NOT_IN_OLD_V2 | 沙盒市場與合成情境訓練 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R149 | Phase 4 | NOT_IN_OLD_V2 | 沙盒教學模式 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R150 | Phase 4 | NOT_IN_OLD_V2 | 通知系統升級 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R151 | Phase 4 | NOT_IN_OLD_V2 | 搜尋與全域查詢 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R152 | Phase 4 | NOT_IN_OLD_V2 | 可自訂儀表板 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R153 | Phase 4 | NOT_IN_OLD_V2 | 最終整合頁 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R154 | Phase 4 | NOT_IN_OLD_V2 | 可視化再升級 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R155 | Phase 4 | NOT_IN_OLD_V2 | 真正的總控台模式 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R156 | Phase 4 | NOT_IN_OLD_V2 | API / 外部整合能力 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R157 | Phase 4 | NOT_IN_OLD_V2 | 法遵 / 使用者警示層 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R158 | Phase 4 | NOT_IN_OLD_V2 | 多語言 / 國際化 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R159 | Phase 4 | NOT_IN_OLD_V2 | 知識傳承與交接模式 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R160 | Phase 4 | NOT_IN_OLD_V2 | 最終治理總表 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |
| R161 | Phase 4 | NOT_IN_OLD_V2 | 系統邊界與禁區總表 | ❌ | MEDIUM | Phase 3-4 topic mismatch affects long-term roadmap |

---

## 高風險校正摘要

### CRITICAL 風險
- **R016**: 凍結基礎設施建立在錯誤主題上。f9b6bba (DecisionTracer) 實作的是「決策來源追溯」，但正確 R016 主題是「欄位命名 / API schema / 資料契約固定」。
  - 影響: _governance/frozen/R016-work-r016-decision-trace-freeze.md、review_memory.txt、auto_mode_governance_guide.md
  - 處置: 已更新所有治理文件中的主題描述，但保留凍結狀態（分支仍受污染，不得 merge）

### HIGH 風險 (Phase 1 主題錯位)
- **R001-R006, R010-R011**: 舊 v2.0 主題與正確主題完全不一致
  - 影響: Phase 1 closure declaration 中的主題對照表
  - 處置: 已更新 closure declaration 與 v2 索引

### MEDIUM 風險 (Phase 2-4 主題錯位)
- **R017-R048**: Phase 2 主題全盤錯位，影響未來輪次規劃
- **R049-R132**: Phase 3 主題全盤錯位
- **R133-R161**: Phase 4 主題需確認（舊 v2 僅有簡短描述）

---

## 已修正檔案清單

1. `_governance/law/161輪正式重編主題總表_唯一基準版_v2.md` - 全量重寫 161 輪主題
2. `_governance/frozen/R016-work-r016-decision-trace-freeze.md` - 更新 R016 主題與說明
3. `_governance/closure/phase1-formal-closure-declaration.md` - 更新 Phase 1 主題對照表
4. `review_memory.txt` - 更新 Section 8 與 Section 10 的 R016 主題
5. `docs/auto_mode_governance_guide.md` - 更新 Section 3A 與 Section 5A 的 R016 主題
6. `manifests/r016_formal_freeze_documentation.yaml` - 更新 topic 欄位
7. `manifests/phase1_formal_closure_declaration.yaml` - 新增 correction_note

---

*本矩陣由 GOV-161-ROUND-LAW-SOURCE-NORMALIZATION 產出*
*狀態：正式治理落地*