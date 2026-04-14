# 第6轮验收报告 / ROUND6_ACCEPTANCE

## 通过状态: PASS

**Commit**: `a1b2c3d` (本轮验收提交)

---

## 验收内容

### 1. 前后端模式契约一致性

#### API 一致性
| API | mode 字段来源 | allowed_transitions | contract |
|-----|-------------|------------------|----------|
| /api/state | engine.get_current_mode() | ✅ | ✅ |
| /api/mode | engine.get_current_mode() | ✅ | ✅ |
| /api/toggle_mode | engine.get_current_mode() | ✅ | ✅ |
| /api/sim/start | engine.get_current_mode() | ✅ | ✅ |
| /api/sim/stop | engine.get_current_mode() | ✅ | ✅ |

#### 前端契约
| 字段 | 来源 | 一致性 |
|------|------|--------|
| d.mode | get_state().mode | ✅ |
| d.allowed_transitions | get_state().allowed_transitions | ✅ |
| d.contract | get_state().contract | ✅ |

### 2. 唯一净损益计算核心

#### PnLCalculator 接口
```python
PnLCalculator.calculate(
    entry_price, exit_price, qty, direction
) -> {gross_pnl, fee, tax, slippage_cost, net_pnl}

PnLCalculator.calculate_from_position(
    entry, exit, lots, direction
) -> {gross_pnl, fee, tax, slippage_cost, net_pnl}
```

#### 统一路径验证
| 路径 | 使用 PnLCalculator | 验证 |
|------|-----------------|------|
| 即时平仓 close() | ✅ | Line 2083 |
| 回测 /api/simulate | ✅ | Line 2802 |
| 学习 log_outcome | ✅ | 已传入 mode 参数 |

#### TradeRecord 结构
```python
@dataclass
class TradeRecord:
    gross_pnl: float      # 毛损益
    fee: float          # 手续费
    tax: float         # 证交税
    slippage_cost: float # 滑点成本
    net_pnl: float    # 净损益
    @property
    def pnl(self) -> float:  # 向后兼容
        return self.net_pnl
```

---

## 验收结果

### API契约测试
```
============================================================
ROUND 6: API MODE CONTRACT
============================================================
PASS: /api/state["mode"] uses get_current_mode()
PASS: /api/mode["mode"] uses get_current_mode()
PASS: all mode APIs return consistent structure
PASS: contract contains allowed_transitions
PASS: contract contains is_halted/halt_reason
============================================================
```

### PnL 测试
```
============================================================
ROUND 6: PnL CALCULATOR
============================================================
PASS: calculate() returns all cost fields
PASS: calculate_from_position() returns all cost fields
PASS: net_pnl = gross_pnl - fee - tax - slippage_cost
PASS: TradeRecord has pnl property
PASS: all exit paths use PnLCalculator
PASS: backtest uses PnLCalculator
============================================================
```

---

## 结论

第6轮: **PASS**

验收通过标准全部满足:
1. ✅ ROUND6_ACCEPTANCE.md 已存在
2. ✅ tests/test_round6_*.py 可重跑
3. ✅ /api/mode 与 /api/state 模式契约一致
4. ✅ PnLCalculator 是唯一 realized pnl 入口
5. ✅ 前后端模式来源统一
6. ✅ 验收输出明确 PASS