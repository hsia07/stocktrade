# Source of Truth - 第3輪定義 (已實現)

## 實現狀態：已完成 ✅

本規則已實現於 `server_v2.py:get_state()` 與 `index_v2.html:render()`。

## 價格 (Price)

| 欄位 | 主來源 | Fallback | 顯示限制 |
|------|-------|---------|----------|
| price | engine.latest_ticks[sym].price | 無 | 交易用 |
| bid | engine.latest_ticks[sym].bid | 無 | 顯示用 |
| ask | engine.latest_ticks[sym].ask | 無 | 顯示用 |
| volume | engine.latest_ticks[sym].volume | 無 | 顯示用 |
| source | tick.source (twse/finmind/cached_real) | "unavailable" | 顯示用，不可交易 |

**實現**：server_v2.py:2078 `self.latest_ticks` → index_v2.html:836 `d.ticks`

## 持倉 (Position)

| 欄位 | 主來源 | Fallback | 顯示限制 |
|------|-------|---------|----------|
| positions | engine.risk.open_positions | {} | 交易用 |
| 前端推算 | 禁止 | N/A | 不得自行推算 |

**實現**：server_v2.py:2080 `self.risk.open_positions` → index_v2.html:765/1000 `d.positions`

## 交易記錄 (Trade/Execution)

| 欄位 | 主來源 | Fallback | 顯示限制 |
|------|-------|---------|----------|
| trades_log | engine.trades_log | [] | 僅顯示 |
| execution | execution_engine API | N/A | 實際下單 |

**實現**：server_v2.py:2088 `[asdict(t) for t in self.trades_log[-30:]]` → index_v2.html:1029 `d.trades_log`

## 新聞/事件 (News/Event)

| 欄位 | 主來源 | Fallback | 顯示限制 |
|------|-------|---------|----------|
| news | 未接入 | N/A | 尚無正式來源 |
| events | 未接入 | N/A | 尚無正式來源 |

**實現**：目前顯���無新聞區塊，無假資料。

## 一致性規則

1. **價格**: 前端僅顯示 `d.ticks`，不自行推算 ✅
2. **持倉**: 前端使用 `d.positions`，不從 trades_log 推算 ✅
3. **交易記錄**: 使用 `d.trades_log`，不與 simData 混用 ✅
4. **衝突處理**: 
   - 真實報價優先於cached ✅
   - 後端持倉優先於前端推算 ✅
   - 模擬數據僅供模擬頁面使用，不得混入真實交易流程 ✅

## 頁面一致性檢查

| 頁面 | 現價來源 | 持倉來源 | 交易記錄來源 | 狀態 |
|------|---------|----------|--------------|------|
| dashboard | d.ticks | d.positions | d.trades_log | ✅ |
| market | d.ticks | - | - | ✅ |
| positions | - | d.positions | - | ✅ |
| trades | - | - | d.trades_log | ✅ |
| robot | d.ticks | d.positions | d.trades_log | ✅ |
| backtest | local simData | local simData | local simData | ✅ |
| sim modal | local simData | local simData | local simData | ✅ |