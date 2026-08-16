#!/usr/bin/env python3
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

UA = "stocktrade-binance-prefilter/1.1"
DEFAULT_BASES = [
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
    "https://fapi3.binance.com",
    "https://fapi4.binance.com",
]
BASES = [x.strip().rstrip("/") for x in os.getenv("BINANCE_BASE_URLS", ",".join(DEFAULT_BASES)).split(",") if x.strip()]
ACTIVE_BASE = None
ENDPOINT_AUDIT = []


def get_json(path, timeout=20):
    global ACTIVE_BASE
    candidates = ([ACTIVE_BASE] if ACTIVE_BASE else []) + [b for b in BASES if b != ACTIVE_BASE]
    failures = []
    for base in candidates:
        url = base + path
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = json.loads(r.read().decode("utf-8"))
                ACTIVE_BASE = base
                ENDPOINT_AUDIT.append({"path": path, "base": base, "status": int(getattr(r, "status", 200))})
                return payload
        except urllib.error.HTTPError as e:
            try:
                body = e.read(300).decode("utf-8", errors="replace")
            except Exception:
                body = ""
            failures.append(f"{base}:HTTP {e.code}:{body[:120]}")
        except Exception as e:
            failures.append(f"{base}:{type(e).__name__}:{e}")
    raise RuntimeError(f"all Binance USD-M endpoints failed for {path}: {' | '.join(failures)}")


def f(x):
    try:
        return float(x)
    except Exception:
        return math.nan


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def records_by_symbol(payload):
    if not isinstance(payload, list):
        raise RuntimeError("expected array payload")
    return {r.get("symbol"): r for r in payload if isinstance(r, dict) and r.get("symbol")}


def main():
    now_ms = int(time.time() * 1000)
    exchange = get_json("/fapi/v1/exchangeInfo")
    tickers = get_json("/fapi/v1/ticker/24hr")
    marks = get_json("/fapi/v1/premiumIndex")
    books = get_json("/fapi/v1/ticker/bookTicker")

    symbols_raw = exchange.get("symbols")
    if not isinstance(symbols_raw, list):
        raise RuntimeError("exchangeInfo symbols[] missing")

    dedup = {r.get("symbol"): r for r in symbols_raw if isinstance(r, dict) and r.get("symbol")}
    contract_counts = {}
    exclusions = {}
    valid = {}
    for s, r in dedup.items():
        ct = str(r.get("contractType", "UNKNOWN"))
        status = r.get("status")
        contract_counts[ct] = contract_counts.get(ct, 0) + 1
        if status == "TRADING" and ct in ("PERPETUAL", "TRADIFI_PERPETUAL"):
            valid[s] = r
        else:
            key = f"status={status}|contractType={ct}"
            exclusions[key] = exclusions.get(key, 0) + 1

    ticker_by = records_by_symbol(tickers)
    mark_by = records_by_symbol(marks)
    book_by = records_by_symbol(books)

    all_three = set(valid) & set(ticker_by) & set(mark_by) & set(book_by)
    missing = []
    pct_values = []
    for s in valid:
        if s not in all_three:
            missing.append({"symbol": s, "ticker": s in ticker_by, "mark": s in mark_by, "book": s in book_by})
            continue
        pct = f(ticker_by[s].get("priceChangePercent"))
        if finite(pct):
            pct_values.append((pct, s))

    pct_values.sort()
    rank = {s: i / max(1, len(pct_values) - 1) for i, (_, s) in enumerate(pct_values)}
    stage1 = []

    for s, meta in valid.items():
        if s not in all_three:
            continue
        t, m, b = ticker_by[s], mark_by[s], book_by[s]
        last = f(t.get("lastPrice")); openp = f(t.get("openPrice")); high = f(t.get("highPrice")); low = f(t.get("lowPrice"))
        pct = f(t.get("priceChangePercent")); qv = f(t.get("quoteVolume")); bid = f(b.get("bidPrice")); ask = f(b.get("askPrice"))
        mark = f(m.get("markPrice")); index = f(m.get("indexPrice")); funding = f(m.get("lastFundingRate"))
        nt = int(m.get("nextFundingTime") or 0); mt = int(m.get("time") or 0); close_time = int(t.get("closeTime") or 0)
        core = (last, openp, high, low, pct, qv, bid, ask, mark, index, funding)
        if not all(finite(x) for x in core):
            missing.append({"symbol": s, "reason": "nonfinite_core_field"})
            continue
        if min(last, openp, bid, ask, index) <= 0 or ask < bid:
            missing.append({"symbol": s, "reason": "invalid_price_or_book"})
            continue

        spread_bps = (ask - bid) / ((ask + bid) / 2) * 10000
        day_range = (high - low) / openp
        premium = mark / index - 1
        reasons, directions = [], []
        if qv >= 10_000_000 and pct >= 8:
            reasons.append("MOMENTUM_LONG"); directions.append("LONG")
        if qv >= 10_000_000 and pct <= -8:
            reasons.append("MOMENTUM_SHORT"); directions.append("SHORT")
        if qv >= 10_000_000 and day_range >= 0.12:
            reasons.append("RANGE_EXPANSION")
        if funding <= -0.003:
            reasons.append("FUNDING_LONG"); directions.append("LONG")
        if funding >= 0.003:
            reasons.append("FUNDING_SHORT"); directions.append("SHORT")
        if abs(premium) >= 0.005:
            reasons.append("PREMIUM_STRESS")
        if reasons:
            stage1.append({
                "symbol": s,
                "contractType": meta.get("contractType"),
                "reasons": sorted(set(reasons)),
                "provisionalDirections": sorted(set(directions)),
                "lastPrice": last,
                "priceChangePercent": pct,
                "quoteVolume": qv,
                "dayRangePct": day_range * 100,
                "spreadBps": spread_bps,
                "fundingRatePct": funding * 100,
                "premiumPct": premium * 100,
                "crossSectionRank01": rank.get(s),
                "nextFundingTime": nt,
                "markTime": mt,
                "closeTime": close_time,
                "ageMs": max(now_ms - close_time, now_ms - mt),
                "perpetualFundingSemantics": nt > mt > 0,
            })

    stage1.sort(key=lambda x: (max(abs(x["priceChangePercent"]) / 8, abs(x["fundingRatePct"]) / 0.30, abs(x["premiumPct"]) / 0.5, x["dayRangePct"] / 12), x["quoteVolume"]), reverse=True)

    audit = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "generatedAtMs": now_ms,
        "source": "Binance official USD-M REST",
        "activeBase": ACTIVE_BASE,
        "endpointAudit": ENDPOINT_AUDIT,
        "exchangeInfoRawDeduped": len(dedup),
        "observedContractTypeCounts": contract_counts,
        "validPerpetual": len(valid),
        "excluded": sum(exclusions.values()),
        "rawEqualsValidPlusExcluded": len(dedup) == len(valid) + sum(exclusions.values()),
        "tickerRaw": len(ticker_by),
        "markRaw": len(mark_by),
        "bookRaw": len(book_by),
        "tickerMatchedValid": len(set(valid) & set(ticker_by)),
        "markMatchedValid": len(set(valid) & set(mark_by)),
        "bookMatchedValid": len(set(valid) & set(book_by)),
        "validWithAllThree": len(all_three),
        "missingCoreCount": len(missing),
        "stage1TriggerCount": len(stage1),
        "exclusionReasonCounts": exclusions,
    }
    complete = audit["rawEqualsValidPlusExcluded"] and audit["validWithAllThree"] == len(valid) and audit["missingCoreCount"] == 0
    out = {"schema": "binance-usdm-prefilter-v1.1", "complete": complete, "audit": audit, "triggers": stage1, "missing": missing[:50]}
    print("SNAPSHOT_JSON=" + json.dumps(out, separators=(",", ":"), ensure_ascii=False))

    artifact_path = os.getenv("BINANCE_PREFILTER_ARTIFACT", "binance_usdm_snapshot.json")
    with open(artifact_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"), ensure_ascii=False)
    print(f"ARTIFACT_PATH={artifact_path}")

    if not complete:
        sys.exit(2)


if __name__ == "__main__":
    main()
