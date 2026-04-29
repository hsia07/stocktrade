# Round Patch Mapping (P0 Governance)

## Purpose
Map recently finalized rounds to their acceptance patches and governance requirements.

## Round Groups and Patches

### Group 1: R027–R032, R043–R049, R052–R053
**Focus**: Local structured decision module + local arbiter

#### Required Patches:
1. **LLM/API Restriction**:
   - LLM/API only for summary/research/auxiliary assistance
   - LLM/API must NOT be used as approval/release mechanism
   - All releases must go through deterministic Final Gate / Risk Layer

2. **Deterministic Final Gate / Risk Layer**:
   - Implement deterministic checks before any trade execution
   - Risk Layer must have veto power over all decisions
   - No LLM override allowed for risk decisions

3. **Append-only Decision Record**:
   - All decisions must be logged in append-only format
   - Decision record must include: timestamp, decision, rationale, actor
   - No deletion or modification of historical decisions

4. **Event Layer Source Credibility Ranking**:
   - Define credibility scores for different event sources
   - Conflict integration rules when sources disagree
   - Unconfirmed high-impact events: MUST result in no-trade / wait-for-confirmation

5. **Taiwan Stock Limits**:
   - Price limits: ±10% (same-day)
   - Settlement: T+2
   - Auction: Opening/closing call auction
   - Trading units: Lot shares (1000 shares) vs odd shares
   - Trading halts / disposal stock handling

### Group 2: R035, R038, R057, R064
**Focus**: L0–L9 validation ladder

#### Required Patches:
1. **L0–L9 Validation Stages**:
   - L0: Syntax check (code style, basic structure)
   - L1: Unit tests (all tests must pass)
   - L2: Integration tests (component interaction)
   - L3: Governance check (evidence package complete)
   - L4: Security scan (no vulnerabilities)
   - L5: Performance test (latency, throughput)
   - L6: Canonical guard check (no direct commits)
   - L7: Merge-pre review (evidence gate passed)
   - L8: Staging deployment (dry-run validation)
   - L9: Production release (live deployment)

2. **No High-Level Validation = No Upgrade to Live**:
   - Must pass L0–L9 before any live deployment
   - Any L-stage failure blocks progression to next stage
   - Evidence of all L-stage passes required in evidence package

### Group 3: R028, R030, R032, R047–R050, R052, R053, R057, R064
**Focus**: Market Reality Layer

#### Required Patches:
1. **Cost Tracking**:
   - Track actual transaction costs (fees, taxes, slippage)
   - Compare against expected costs
   - Alert on significant deviations

2. **Slippage Monitoring**:
   - Measure actual vs expected slippage
   - Implement slippage veto for large deviations
   - Log all slippage events

3. **Liquidity Veto**:
   - Check available liquidity before order placement
   - Veto orders that would exceed liquidity thresholds
   - Implement capacity limits

4. **Partial Fill Handling**:
   - Handle partial order fills gracefully
   - Track partial fill rates and reasons
   - Implement retry/adjustment logic

5. **Capacity Management**:
   - Track system capacity (orders/sec, concurrent positions)
   - Implement capacity veto when near limits
   - Scale resources proactively

6. **Expected vs Actual Drift**:
   - Monitor drift between expected and actual outcomes
   - Alert on significant drift
   - Adjust models/strategies based on drift analysis

### Group 4: Global Blocked Patches
**Focus**: Phase B usage chain

#### Required Patches:
1. **Phase B Usage Chain Remains BLOCKED**:
   - Block all Phase B features until:
     - Machine-readable usage source exists
     - Source is non-interactive (no manual intervention)
     - Source is stable (consistent format, reliable)
     - Source includes quota/reset_time information
   - Current status: `usage_source_available = FALSE`
   - Blocked features:
     - Usage exhausted auto-save checkpoint
     - Usage exhausted auto-pause
     - Waiting for usage reset
     - Periodic usage check
     - Usage recovery auto-resume

### Group 5: R031
**Focus**: Confidence calibration

#### Required Patches:
1. **Confidence Calibration**:
   - Raw confidence must NOT be directly added/compared
   - Calibration against historical performance required
   - Calibrated confidence only for decision making

2. **Raw Confidence Restrictions**:
   - Raw confidence cannot be used as trade approval basis
   - Must use calibrated confidence scores
   - Validation: `confidence_calibrated: true` in evidence.json

### Group 6: R041, R074, R091
**Focus**: Regime switching enhancement

#### Required Patches:
1. **Regime Switching Logic**:
   - offline labeler vs online filter separation
   - filtered posterior only for decisions
   - posterior threshold / entropy gate
   - minimum dwell time between switches
   - hysteresis to prevent flapping
   - switch cost calculation

2. **Regime Uncertainty Control**:
   - Use entropy or equivalent metrics
   - High uncertainty => reduce-size / wait-confirmation / no-trade only
   - Validation: `regime_uncertainty <= threshold` before trade

### Group 7: R043–R046, R064
**Focus**: As-of snapshot / tradable timestamp contract

#### Required Patches:
1. **Timestamp Contracts**:
   - publish_ts / ingest_ts / tradable_ts / source_ts / decision_ts
   - decision_ts MUST be >= tradable_ts (Rule 1: future leak FAIL)
   - As-of snapshot consistency across all layers

2. **Tradable Timestamp Enforcement**:
   - Data not tradable until tradable_ts
   - All decisions must use data with valid tradable_ts
   - Validation: `timestamp_integrity` in evidence_checker.py

### Group 8: R047–R050, R078, R117
**Focus**: Execution benchmark decomposition

#### Required Patches:
1. **Benchmark Components**:
   - implementation shortfall / fill prob / partial fill
   - cancel-fill race / ack timeout
   - per-session benchmark tracking

2. **Execution Quality Metrics**:
   - expected fill vs actual fill deviation tracking
   - expected slippage vs actual slippage monitoring
   - Deviation > threshold => MUST downgrade or recalibrate

### Group 9: R047, R053, R070, R153
**Focus**: Borrow / margin matrix

#### Required Patches:
1. **Borrow Availability**:
   - Real-time borrow availability checks
   - stale borrow data (>N min) => NO trade
   - Validation: `borrow_status_fresh: true` in evidence.json

2. **Margin Requirements**:
   - margin requirement calculation
   - maintenance buffer tracking
   - forced liquidation risk assessment

3. **Portfolio Risk (R070)**:
   - Aggregate risk across all positions
   - Portfolio-level exposure limits
   - Correlation-aware risk calculations
   - Combination total exposure caps
   - Single target position limits
   - Continuous idle auto-shutdown (辅助监控，非核心替代)

4. **Borrow / Margin Matrix (R070 涵盖)**:
   - Borrow availability real-time checks
   - Margin requirement calculation
   - Maintenance buffer tracking
   - Forced liquidation risk assessment

### Group 10: R051
**Focus**: Risk budget visualization

#### Required Patches:
1. **Visualization Components**:
   - Risk snapshot display
   - Expected cost / expected slippage / expected net RR visualization
   - Real-time risk budget tracking
   - Historical trend charts for risk metrics

### Group 11: R057, R064, R077, R110
**Focus**: Parameter fragility / search ledger / benchmark-universe governance

#### Required Patches:
1. **Parameter Stability**:
   - Island-type optimal parameters => mark overfit risk
   - No plateau/stability evidence => NO upgrade paper/live
   - Parameter search ledger for reproducibility

2. **Benchmark-Universe Consistency**:
   - survivor-only universe => NO upgrade
   - PRI-TRI benchmark mixing => NO upgrade
   - universe inconsistency between train/validation/live => NO upgrade

### Group 12: R068
**Focus**: MarketContext / ctx append-only decision record (enhanced)

#### Required Patches:
1. **Append-only Decision Record**:
   - MarketContext preserved across decision points
   - ctx.trace_id for decision tracing
   - decision_chain linking related decisions
   - threshold/config version tracking
   - No silent context loss allowed

### Group 13: R074, R083, R117
**Focus**: Sequential kill-switch statistics

#### Required Patches:
1. **Sequential Monitoring**:
   - CUSUM (Cumulative Sum) control charts
   - SPRT (Sequential Probability Ratio Test)
   - Sequential anomaly detection
   - Kill-switch trigger logic

### Group 14: R0416 Law Integration Gap
**Focus**: Law 04 integration gap acknowledgment

#### Required Patches:
1. **Current Status: NOT Complete Integration Package**:
   - Law 04 (0416 修正版) published but NOT fully integrated
   - Requires: candidate pre-review + merge + post-merge repo full audit
   - All rounds need 逐轮法条补正 to fully align with Law 04

2. **Required Actions**:
   - All existing candidates need re-review against Law 04
   - All future candidates must explicitly reference Law 04 compliance
   - Post-merge repo-wide audit needed to close integration gap
   - 02 > 03 > 04 > 01 (priority order)

3. **Evidence Checker Update Needed**:
   - `automation/control/evidence_checker.py` must add Law 04 compliance check
   - Each candidate evidence.json must include `law_compliance: "04"`
   - Merge-decision ready only when Law 04 compliance verified

## F. Core Formula Governance Patches

Add to evidence_checker.py validation:

1. **net_edge = p̂ * Ŵ - (1-p̂) * L̂ - C - S - B - T**
   - Validate: `net_edge > 0` for trade approval
   - Evidence must show calculation with calibrated inputs

2. **qty = min(trade_budget/risk_unit, adv_cap, exposure_cap, margin_cap, regime_cap)**
   - Validate: All cap checks performed
   - Evidence must show min() applied correctly

3. **Regime uncertainty control**:
   - Use entropy or equivalent metrics
   - Validate: `regime_uncertainty <= threshold`

4. **Release conditions (ALL must pass)**:
   - `net_edge > 0`
   - `fill_prob >= threshold`
   - `regime_uncertainty <= threshold`
   - `no veto`
   - `market reality pass`
   - `risk final gate pass`

## Validation Checkpoints

### For Each Round Group:
1. Verify all patches are implemented
2. Verify patch tests exist and pass
3. Verify evidence package includes patch validation
4. Verify no Phase B features leak into Phase A/B locked rounds

### Governance Gates:
- **Pre-commit**: Check for Phase B feature leaks
- **Merge-pre**: Verify patch mapping completeness
- **Post-merge**: Validate all patches present in canonical

## Related Files:
- `_governance/audit/canonical_guard_specification.md`
- `_governance/audit/merge_pre_evidence_gate.md`
- `_governance/audit/round_patch_mapping.md` (this file)
- `_governance/audit/global_fail_rules.md`
- `automation/control/evidence_checker.py` (validates evidence)
- `automation/control/candidate_checker.py` (validates candidates)

## Maintenance:
- Update this file when new rounds are finalized
- Map new rounds to appropriate groups
- Ensure patch requirements are reflected in evidence checker
