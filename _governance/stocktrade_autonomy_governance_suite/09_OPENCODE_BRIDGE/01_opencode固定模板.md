# opencode 固定模板規範

## 目標
把高階規則轉成固定格式，避免本地 agent 接收的指令漂移。

## 固定輸出區塊
1. ROUND_CONTEXT
2. STRICT_REQUIREMENTS
3. EXECUTION_OUTPUT

## 強制欄位
- 輪次
- 主題
- 本次只修
- 禁止事項
- 通過標準
- 直接 FAIL 條件
- 必交證據
- REPLY_ID

## 禁止
- opencode 不得自行宣判通過
- opencode 不得修改母表標準
- opencode 不得偷加未經核准的新要求
