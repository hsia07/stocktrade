# R027: 套利保护机制 (Arbitrage Protection Mechanism)

## Authoritative Topic
- **R027** = `套利 / 套利保护机制` (from 161轮正式重编主题总表_唯一基准版_v2.md)
- **Topic A**: 套利 / 套利保护机制 ✓
- **Topic B**: 开盘 / 收盘保护机制 ✗ (no repo-internal evidence)

## Task Type
R027 arbitrage protection mechanism implementation (protection-first, no execution)

## Scope
### Allowed (Minimal File Scope)
- `modules/strategy/arbitrage_protection.py` (new - protection mechanism only)
- `modules/risk/arbitrage_risk_gate.py` (new - Risk Layer integration)
- `modules/market_reality/arbitrage_slippage_model.py` (new - Market Reality integration)
- `tests/test_arbitrage_protection.py` (new)
- `docs/arbitrage_strategy.md` (new)
- `automation/control/candidates/R027-ARBITRAGE-PROTECTION/` (evidence package)

### Forbidden
- `modules/strategy/arbitrage_execution.py` (no execution)
- `tests/test_arbitrage_execution.py` (no execution tests)
- `modules/execution/broker_*.py` (no broker changes)
- `modules/execution/order_*.py` (no order placement changes)
- `services/runtime/*.py` (no runtime modifications)
- Any stocktrade_connected features
- Any R028+ planning extensions
- Any LINE / line-personal-butler / VM files

## Required Capabilities (Protection Only)
- Arbitrage opportunity safety check (NOT execution)
- Gross-to-net arbitrage viability after fees/tax/slippage
- Liquidity veto / no-trade decision
- Market reality unfavorable → veto / reduce / abort
- Risk Gate integration (position / exposure / loss / limit checks)
- Pre-trade arbitrage protection report with reason codes

## Taiwan Market Constraints (Must Be Enforced)
- **涨跌幅限制**: ±10% (price must stay within limit)
- **T+2 交割**: Settlement occurs 2 business days after trade
- **集合竞价**: 08:30-09:00 (pre-market auction)
- **盘中交易**: 09:00-13:30 (continuous trading)
- **零股交易**: 13:40-14:30 (odd lots, different lot size)
- **零股整股差异**: Different pricing and liquidity
- **流动性不足 veto**: If bid/ask spread too wide or volume insufficient
- **融券限制**: Short selling constraints may affect arbitrage
- **当冲限制**: Day trading constraints may affect timing

## Market Reality Constraints
- **成本模型**: Transaction costs (fees, taxes, impact cost) subtracted from gross profit
- **滑价模型**: Slippage modeled (expected vs actual execution price)
- **成交率模型**: Fill rate probability (may not fill 100% of intended volume)
- **Partial fill 处理**: If only partially filled, adjust position and risk
- **不可成交场景**: If market conditions prevent execution, gracefully cancel
- **流动性成本**: Larger volumes may incur higher slippage
- **时间衰减**: Arbitrage opportunities disappear quickly, execution speed matters
- **跨市场差异**: Spot vs futures vs ETF may have different reality constraints

## Risk Layer Constraints
- **Deterministic Risk Layer / Final Gate 不得被套利保护机制绕过**
- **套利策略必须通过 Risk Layer 所有检查** (position limit, exposure limit, loss limit)
- **套利保护机制优先于套利执行** (protection first)
- **Risk veto 必须能阻断套利**: liquidity insufficient / risk limit breached / market reality unfavorable
- **不得套用美股/crypto 假设** (美股无涨跌幅，crypto 24/7 交易)
- **套利单位必须纳入整体 portfolio risk 计算**
- **套利策略不得增加整体 portfolio risk exposure beyond limits**
- **Final Gate 必须在套利执行前确认**: Market Reality + Risk Layer + Taiwan Market Constraints all pass

## Evidence Package
Path: `automation/control/candidates/R027-ARBITRAGE-PROTECTION/`
- `task.txt`: Task description and parameters
- `evidence.json`: Contains `law_compliance: "04"`
- `report.json`: Commit hash and validation results
- `candidate.diff`: Git diff of all changes
- `no-aider-used.txt`: Confirms no aider used
- `test-results.txt`: All validation criteria passed

## Machine-Checkable Checks
- [x] Arbitrage protection module exists
- [x] Risk gate module exists
- [x] Market reality slippage model exists
- [x] No `arbitrage_execution.py`
- [x] No broker/order/runtime core modifications
- [x] Taiwan market constraints enforced in code/tests/docs
- [x] Liquidity veto path exists
- [x] Cost/slippage/fill-rate logic participates in protection decision
- [x] Deterministic Risk Layer / Final Gate veto path exists
- [x] Evidence package 6/6 complete

## Acceptance Criteria
- [x] R027 authoritative topic confirmed: `套利 / 套利保护机制`
- [x] Arbitrage protection mechanism implemented and tested
- [x] Risk Layer / Final Gate integration verified
- [x] Market Reality Layer integration verified
- [x] Taiwan market constraints (±10%, T+2, 集合竞价/盘中/零股, 流动性 veto) enforced
- [x] Liquidity veto functional
- [x] No 美股/crypto assumptions
- [x] All machine-checkable checks passed
- [x] Single commit candidate (or justified multi-commit)
- [x] 6/6 evidence package with `law_compliance: "04"`
- [x] No broker/order core modifications
- [x] No runtime changes
- [x] User signoff obtained before merge

## Implementation Notes
- **Protection-first**: Only safety checks, no trade execution
- **No broker integration**: No connection to broker APIs
- **No order placement**: No actual trade orders sent
- **Deterministic Risk Layer**: Must not be bypassed by protection mechanism
- **Taiwan market reality**: All assumptions must be Taiwan-specific (no US/crypto)

## Commit Structure
- **SINGLE COMMIT ONLY**: One commit containing:
  - 3 new modules (protection, risk gate, market reality)
  - 1 test file
  - 1 documentation file
  - 6/6 evidence package
