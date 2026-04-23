# Phase 1 API Schema / Data Contract Snapshot
## R016: Field Naming / API Schema / Data Contract Fixation

**Document Version:** 1.0.0
**Canonical Commit:** 6a221306995bc40ce3ab9e0e91cdf294dd957417
**Scope:** Phase 1 (R001-R016) finalized API contract

---

## Schema Version

All `/api/state` responses include:
```json
{
  "schema_version": "1.0.0"
}
```

Future breaking changes must increment this version.

---

## API Endpoints

### 1. GET /api/state
**Primary state exposure endpoint.**

**Response Keys (guaranteed stable):**
| Key | Type | Added By | Description |
|-----|------|----------|-------------|
| schema_version | string | R016 | API schema version identifier |
| ticks | dict | baseline | Latest price ticks per symbol |
| agents | dict | baseline | Agent analysis reports |
| positions | dict | baseline | Open positions |
| daily_pnl | float | baseline | Daily P&L |
| daily_trades | int | baseline | Daily trade count |
| is_halted | bool | baseline | Trading halt status |
| trades_log | list | baseline | Recent trade records |
| timestamp | string | baseline | Current time HH:MM:SS |
| mode | string | baseline | PAPER or LIVE |
| auto_trade | bool | baseline | Auto trading enabled |
| artifact_stats | dict | R011 | Artifact manager statistics |
| health_status | dict | R006 | Health monitor aggregate status |
| circuit_breaker | dict | R006 | Circuit breaker status |
| degradation_strategy | string/null | R006 | Current degradation strategy |
| r008_mode | string | R008 | Mode controller mode enum |
| mode_allows_trading | bool | R008 | Whether current mode allows trading |
| mode_transition_count | int | R008 | Number of mode transitions recorded |
| r009_queue | dict | R009 | Priority scheduler queue status |
| r009_alerts | list | R009 | Priority monitor alerts |

**Compatibility Rule:** All keys listed above are frozen for Phase 1. New keys may be added in future phases but existing keys must not be removed or renamed without a schema_version bump.

---

### 2. GET /api/trades
**Trade history endpoint.**

**Response:** Array of TradeRecord objects

---

### 3. POST /api/toggle_mode
**Toggle trading mode.**

**Request Body:** (mode string)
**Response:** {mode, paper_trade, auto_trade}

---

### 4. GET /api/mode
**Current mode query.**

**Response Keys:**
| Key | Type |
|-----|------|
| mode | string |
| paper_trade | bool |
| auto_trade | bool |

---

### 5. POST /api/mode_transition
**R008: Mode transition with validation and recording.**

**Request Body:** {from_mode, to_mode, reason}
**Response:** {status, from_mode, to_mode, requires_approval, current_mode, paper_trade, auto_trade}

---

### 6. GET /api/mode_history
**R008: Mode transition history.**

**Response Keys:**
| Key | Type |
|-----|------|
| transitions | list |
| current_mode | string |

---

### 7. GET /api/priority_status
**R009: Priority queue status (advisory only).**

**Response Keys:**
| Key | Type | Description |
|-----|------|-------------|
| queue | dict | Queue statistics |
| execution_history_count | int | Number of executed tasks |
| advisory_only | bool | Always true |
| note | string | Advisory disclaimer |

---

### 8. GET /api/priority_alerts
**R009: Priority system alerts (advisory only).**

**Response Keys:**
| Key | Type |
|-----|------|
| alerts | list |
| metrics | list |
| advisory_only | bool | Always true |

---

## Field Naming Rules

1. **snake_case** for all JSON keys
2. **RXXX prefix** for round-specific state fields (e.g., r008_mode, r009_queue)
3. **Immutable keys** - once added to /api/state, keys cannot be renamed in the same schema_version
4. **Additive only** - new fields may be added; removal requires schema_version bump
5. **Null safety** - all fields must handle null/undefined gracefully on the consumer side

## Compatibility Guarantee

- **Phase 1 schema_version "1.0.0"** is frozen
- All endpoints and response keys documented above are guaranteed stable within Phase 1
- Breaking changes require new schema_version and Phase 2+ governance approval
