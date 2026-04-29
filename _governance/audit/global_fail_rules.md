# Global FAIL/BLOCK Rules (P0+ Trading Logic)

## Purpose
Define mandatory FAIL/BLOCK rules for trading logic, risk control, regime detection, and formula governance.
These rules must be enforced by validators and checked during merge-pre review.

## A. Timestamp & Data Integrity Rules

### Rule 1: future leak / decision_ts < tradable_ts => FAIL
- **Condition**: If `decision_ts` (when decision was made) is earlier than `tradable_ts` (when data became tradable)
- **Action**: FAIL immediately
- **Reason**: Future leak - using data that wasn't available at decision time
- **Validator**: Check `decision_ts >= tradable_ts` in evidence_checker.py

### Rule 2: Uncalibrated confidence => BLOCK trading approval
- **Condition**: If confidence score is not calibrated against historical performance
- **Action**: BLOCK as trading approval basis
- **Reason**: Uncalibrated confidence scores are misleading
- **Validator**: Check `confidence_calibrated: true` in evidence.json

## B. Universe & Benchmark Rules

### Rule 3: survivor-only universe / PRI-TRI mix / universe inconsistency => NO upgrade
- **Condition**: If using survivor-only universe, or mixing PRI-TRI benchmarks, or universe inconsistency between training/validation/live
- **Action**: BLOCK upgrade to paper/live
- **Reason**: Biased universe leads to overfitting
- **Validator**: Check universe consistency in evidence_checker.py

### Rule 4: stale borrow availability / margin / shortable status => NO trade
- **Condition**: If borrow availability data is stale (>N minutes old), or margin requirements changed, or shortable status outdated
- **Action**: BLOCK all trades for that instrument
- **Reason**: Stale borrow data leads to failed shorts
- **Validator**: Check `borrow_status_fresh: true` in evidence.json

## C. Execution Quality Rules

### Rule 5: expected vs actual fill deviation / expected slippage vs actual slippage => MUST downgrade or recalibrate
- **Condition**: If |expected_fill - actual_fill| > threshold, or |expected_slippage - actual_slippage| > threshold
- **Action**: MUST downgrade model or recalibrate immediately
- **Reason**: Model drift detected
- **Validator**: Check slippage deviation in evidence_checker.py

## D. Regime Uncertainty Rules

### Rule 6: regime uncertainty too high => reduce-size / wait-confirmation / no-trade only
- **Condition**: If regime uncertainty (entropy or equivalent metric) exceeds threshold
- **Action**: ONLY allow reduce-size, wait-confirmation, or no-trade
- **Reason**: High uncertainty = high risk of wrong regime classification
- **Validator**: Check `regime_uncertainty <= threshold` before trade approval

## E. Parameter Stability Rules

### Rule 7: island-type optimal parameters / no plateau/stability evidence => mark overfit risk, NO upgrade
- **Condition**: If optimal parameters found via grid search but no plateau/stability evidence
- **Action**: Mark as overfit risk, BLOCK upgrade to paper/live
- **Reason**: Island optima are not robust
- **Validator**: Check `parameter_search_has_plateau: true` in evidence.json

## Integration with Evidence Checker

Add these checks to `automation/control/evidence_checker.py`:

```python
def validate_trading_logic(self, evidence_dir):
    """Validate trading logic rules."""
    # Rule 1: Check timestamp integrity
    if not self._check_timestamp_integrity(evidence_dir):
        self.errors.append("FAIL: future leak detected (decision_ts < tradable_ts)")
    
    # Rule 2: Check confidence calibration
    if not self._check_confidence_calibrated(evidence_dir):
        self.errors.append("BLOCK: uncalibrated confidence cannot be used for trade approval")
    
    # Add more rule checks...
```

## Mapping to Rounds

| Rule | Affected Rounds |
|------|-----------------|
| Rule 1 (timestamp) | R043-R046, R064 |
| Rule 2 (confidence) | R031, R057, R077, R110 |
| Rule 3 (universe) | R057, R064, R077, R110 |
| Rule 4 (borrow/margin) | R047, R053, R070, R153 |
| Rule 5 (fill/slippage) | R047-R050, R078, R117 |
| Rule 6 (regime) | R041, R074, R091 |
| Rule 7 (parameters) | R057, R064, R077, R110 |

## Related Files
- `_governance/audit/global_fail_rules.md` (this file)
- `automation/control/evidence_checker.py` (implements validation)
- `_governance/audit/round_patch_mapping.md` (maps rules to rounds)
