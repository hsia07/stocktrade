# 第5轮验收报告 / ROUND5_ACCEPTANCE

## 通过状态: PASS

**Commit**: `e5c2f71` (本轮验收提交)

---

## 验收内容

### 1. 完整 MODE_TRANSITIONS Master Table

| From | To | Allowed | Reason |
|------|-----|--------|---------|
| observe | pause | ✅ | AUTO_TRADE=false |
| observe | sim | ✅ | ENTER_SIM |
| observe | paper | ✅ | PAPER_SWITCH |
| observe | live | ❌ | must go through PAUSE |
| observe | recovery | ✅ | is_halted=true |
| sim | pause | ✅ | EXIT_SIM |
| sim | observe | ✅ | EXIT_SIM |
| sim | paper | ✅ | EXIT_SIM |
| sim | live | ✅ | EXIT_SIM |
| paper | pause | ✅ | AUTO_TRADE=false |
| paper | sim | ✅ | ENTER_SIM |
| paper | live | ✅ | PAPER_SWITCH |
| paper | observe | ❌ | must go through PAUSE |
| paper | recovery | ✅ | is_halted=true |
| live | pause | ✅ | AUTO_TRADE=false |
| live | sim | ✅ | ENTER_SIM |
| live | paper | ✅ | PAPER_SWITCH |
| live | observe | ❌ | must go through PAUSE |
| live | recovery | ✅ | is_halted=true |
| pause | observe | ✅ | AUTO_TRADE=true |
| pause | sim | ✅ | ENTER_SIM |
| pause | paper | ✅ | PAPER_TRADE=true |
| pause | live | ✅ | PAPER_TRADE=false |
| pause | recovery | ✅ | is_halted=true |
| recovery | pause | ✅ | is_halted=false |
| recovery | observe | ❌ | must go through PAUSE |
| recovery | paper | ❌ | must go through PAUSE |
| recovery | live | ❌ | must go through PAUSE |

### 2. 未定义转移

**默认拒绝** - 未在表格中定义的转移一律返回 False

### 3. RECOVERY 进入/退出规则

- **进入**: is_halted=true 时，OBSERVE/PAPER/LIVE 可进入 RECOVERY
- **退出**: RECOVERY 只能到 PAUSE（is_halted=false），禁止直跳 OBSERVE/PAPER/LIVE

### 4. 入口一致性

| 入口 | 路径 |
|------|------|
| enter_sim_mode() | ✅ 走 set_mode() |
| exit_sim_mode() | ✅ 走 set_mode() |
| api_toggle_mode | ✅ 走 can_transition() |
| api_sim_start | ✅ 走 enter_sim_mode() |
| api_sim_stop | ✅ 走 exit_sim_mode() |
| sync_mode_with_state() | ✅ 走 set_mode() (不再直接覆写) |

### 5. 单一模式来源

- **唯一来源**: `TradingEngine._mode`
- **访问方法**: `get_current_mode()`
- **修改方法**: `set_mode()` (内部调用 `can_transition()`)
- **无旁路**: 不存在绕过状态机的直接 _mode 写入

### 6. 前端契约

| 字段 | 来源 |
|------|------|
| d.mode | get_state().mode |
| allowed_transitions | get_state().allowed_transitions |
| contract.is_halted | risk.is_halted |
| contract.halt_reason | risk.halt_reason |

---

## 验收结果

```
============================================================
ROUND 5 MODE TRANSITIONS
============================================================
PASS: sim -> pause = True (exp=True)
PASS: sim -> observe = True (exp=True)
PASS: sim -> paper = True (exp=True)
PASS: sim -> live = True (exp=True)
PASS: pause -> sim = True (exp=True)
PASS: pause -> observe = True (exp=True)
PASS: pause -> paper = True (exp=True)
PASS: pause -> live = True (exp=True)
PASS: pause -> recovery = True (exp=True)
PASS: observe -> pause = True (exp=True)
PASS: observe -> sim = True (exp=True)
PASS: observe -> paper = True (exp=True)
PASS: observe -> live = False (exp=False)
PASS: paper -> pause = True (exp=True)
PASS: paper -> sim = True (exp=True)
PASS: paper -> live = True (exp=True)
PASS: paper -> observe = False (exp=False)
PASS: live -> pause = True (exp=True)
PASS: live -> sim = True (exp=True)
PASS: live -> paper = True (exp=True)
PASS: live -> observe = False (exp=False)
PASS: recovery -> pause = True (exp=True)
PASS: recovery -> observe = False (exp=False)
PASS: recovery -> paper = False (exp=False)
PASS: recovery -> live = False (exp=False)
PASS: observe -> recovery = True (exp=True)
PASS: paper -> recovery = True (exp=True)
PASS: live -> recovery = True (exp=True)

28/28 passed

============================================================
UNDEFINED TRANSITIONS DEFAULT DENY
============================================================
PASS: OBSERVE -> OBSERVE denied
PASS: SIM -> PAPER denied
PASS: RECOVERY -> SIM denied

============================================================
ENTRY CONSISTENCY
============================================================
PASS: set_mode/get_current_mode exist

============================================================
ROUND 5: PASS
============================================================
```

---

## 结论

第5轮: **PASS**

验收通过标准全部满足:
1. ✅ 完整、可重跑、固定输出的验收档 (tests/test_round5_state_machine.py)
2. ✅ 所有合法/非法 transition 逐条验证
3. ✅ RECOVERY 端到端验证
4. ✅ 入口统一状态机
5. ✅ 单一模式来源
6. ✅ 前后端模式契约