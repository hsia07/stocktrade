# NEA Long-Term Patch Registry

## 概述
本 registry 提供 stocktrade NEA（Net Expected Advantage）引擎的长期补丁结构化注册表，供 R028-R100 轮次自动注入使用。

## 文件信息
- **Registry 文件**: `automation/control/patch_registry/nea_long_term.yaml`
- **Law Compliance**: 04
- **来源**: NEA long-term patch registry structuring audit
- **类型**: capability/constraint/acceptance based（非 file-name hard-lock）

## 核心原则（已修正审计污染点）
1. **Round-Scoped Injection（非全局）**:
   - `patch_scope` 已修正为 round-scoped（非 `global R028-R100`）
   - 按轮次自动注入：R028-R033（v0.1 mandatory），R034-R100（v0.2/v1.0 roadmap only）

2. **文件名非硬锁定**:
   - 注入内容是 capability/constraint/acceptance
   - 非特定文件名（避免 `patch_name` 直接等同 implementation 文件名）

3. **v0.1 vs v0.2/v1.0 严格分离**:
   - v0.1 mandatory: R028-R033（基础集成）
   - v0.2 roadmap: R034-R070（高级模型，不可提前注入 v0.1）
   - v1.0 roadmap: R071-R100（完整堆栈，不可提前注入 v0.1/v0.2）

## Registry 结构
```yaml
patch_namespace: NEA_LONG_TERM
global_guardrails: [6 items]  # 适用于所有轮次
round_patch_map: [R028-R100]  # round-scoped injection
phased_delivery_plan: [v0.1, v0.2, v1.0]  # phase-gated
acceptance_overrides: [v0.1 mandatory, v0.2/v1.0 blocker]
blocker_rules: [7 items]  # 适用于所有轮次
evidence_requirements: [trace_id, replay_log, etc.]
```

## 自动注入目标轮次（v0.1 mandatory）
- **R028**: Market Reality Layer（cost/slippage/fill）
- **R029**: Cost/Slippage/Fill Probability modeling
- **R030**: Latency/Tail Risk/Uncertainty variables
- **R031**: Trace/Replay/Evidence Package
- **R032**: Append-only audit log
- **R033**: Library layering（Pydantic/scikit-learn）

## Roadmap Only（不可注入 v0.1/v0.2）
- **R034-R050**: v0.2 特性（latency optimization, tail risk）
- **R051-R070**: 高级风险模型（v0.2/v1.0）
- **R071-R100**: 完整堆栈集成（v1.0 only）

## 关键保护机制
1. **NEA deterministic gate = final authority**
2. **No LLM/AI override** for risk decisions
3. **Taiwan market constraints mandatory**（±10%, T+2, 集合竞价, 零股/整股）
4. **Market Reality Layer mandatory** in relevant rounds
5. **Trace/Replay/Evidence Package mandatory** in relevant rounds

## Blocker Rules（适用于所有轮次）
- BLOCK: LLM/AI override attempts
- BLOCK: Missing Market Reality Layer（如适用）
- BLOCK: Missing proper evidence package（6/6, law_compliance: 04）
- BLOCK: Modifying append-only audit log
- BLOCK: Injecting v1.0 features into v0.1
- BLOCK: Bypassing Taiwan market constraints
- BLOCK: Using file-name hard-lock instead of capability/constraint

## 使用方式
未来轮次（R028+）candidate 创建时，自动化工具将：
1. 读取 `automation/control/patch_registry/nea_long_term.yaml`
2. 根据轮次编号（如 R028）查找对应 `round_patch_map`
3. 按 `injection_type`（mandatory/roadmap_only）注入 capabilities/constraints
4. 验证 `acceptance_overrides` 和 `blocker_rules`
5. 在 evidence.json 中包含 `patched_with: NEA_LONG_TERM` 和 `law_compliance: 04`

## 禁止事项
- ❌ 不得将 registry 直接作为 R028 implementation（本论只做 registry 落地）
- ❌ 不得提前注入 v0.2/v1.0 特性到 v0.1 轮次
- ❌ 不得使用文件名硬锁定代替 capability/constraint 描述
- ❌ 不得绕过 NEA deterministic gate

## Evidence Package
本 registry implementation 包含完整 6/6 evidence package：
- `task.txt`: 任务描述和参数
- `evidence.json`: 包含 `law_compliance: 04`
- `report.json`: Commit hash 和验证结果
- `candidate.diff`: Git diff
- `no-aider-used.txt`: 确认未使用 aider
- `test-results.txt`: 所有验证标准通过

## 验证标准
✓ `nea_registry_created_true_or_false = TRUE`
✓ `nea_registry_human_readable_doc_created_true_or_false = TRUE`
✓ `round_scoped_injection_preserved_true_or_false = TRUE`
✓ `v0_1_vs_v0_2_v1_0_separation_preserved_true_or_false = TRUE`
✓ `file_name_hard_lock_avoided_true_or_false = TRUE`
✓ `auto_injection_targets_r028_to_r033_true_or_false = TRUE`
✓ `implementation_not_started_true_or_false = TRUE`
✓ `evidence_package_complete_6_of_6_true_or_false = TRUE`
✓ `evidence_json_contains_law04_true_or_false = TRUE`
