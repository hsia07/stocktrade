#!/usr/bin/env python3
import json
import math
import sys
import time
import urllib.request
from datetime import datetime, timezone

BASE = "https://fapi.binance.com"
UA = "stocktrade-binance-prefilter/1.0"


def get_json(path, timeout=20):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def f(x):
    try:
        return float(x)
    except Exception:
        return math.nan


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def main():
    now_ms = int(time.time() * 1000)
    exchange = get_json("/fapi/v1/exchangeInfo")
    tickers = get_json("/fapi/v1/ticker/24hr")
    marks = get_json("/fapi/v1/premiumIndex")
    books = get_json("/fapi/v1/ticker/bookTicker")

    symbols_raw = exchange.get("symbols")
    if not isinstance(symbols_raw, list):
        raise RuntimeError("exchangeInfo symbols[] missing")

    dedup = {}
    contract_counts = {}
    exclusions = {}
    for r in symbols_raw:
        s = r.get("symbol")
        if not s:
            continue
        dedup[s] = r
    for r in dedup.values():
        ct = str(r.get("contractType", "UNKNOWN"))
        contract_counts[ct] = contract_counts.get(ct, 0) + 1

    valid = {}
    for s, r in dedup.items():
        status = r.get("status")
        ct = r.get("contractType")
        if status == "TRADING" and ct in ("PERPETUAL", "TRADIFI_PERPETUAL"):
            valid[s] = r
        else:
            key = f"status={status}|contractType={ct}"
            exclusions[key] = exclusions.get(key, 0) + 1

    ticker_by = {r.get("symbol"): r for r in tickers if isinstance(r, dict) and r.get("symbol")}
    mark_by = {r.get("symbol"): r for r in marks if isinstance(r, dict) and r.get("symbol")}
    book_by = {r.get("symbol"): r for r in books if isinstance(r, dict) and r.get("symbol")}

    matched_ticker = set(valid) & set(ticker_by)
    matched_mark = set(valid) & set(mark_by)
    matched_book = set(valid) & set(book_by)

    stage1 = []
    missing = []
    pct_values = []
    for s in valid:
        t = ticker_by.get(s)
        m = mark_by.get(s)
        b = book_by.get(s)
        if not t or not m or not b:
            missing.append({"symbol": s, "ticker": bool(t), "mark": bool(m), "book": bool(b)})
            continue
        pct = f(t.get("priceChangePercent"))
        if finite(pct):
            pct_values.append((pct, s))

    pct_values.sort()
    rank = {s: i / max(1, len(pct_values) - 1) for i, (_, s) in enumerate(pct_values)}

    for s, meta in valid.items():
        t = ticker_by.get(s)
        m = mark_by.get(s)
        b = book_by.get(s)
        if not t or not m or not b:
            continue
        last = f(t.get("lastPrice"))
        openp = f(t.get("openPrice"))
        high = f(t.get("highPrice"))
        low = f(t.get("lowPrice"))
        pct = f(t.get("priceChangePercent"))
        qv = f(t.get("quoteVolume"))
        bid = f(b.get("bidPrice"))
        ask = f(b.get("askPrice"))
        mark = f(m.get("markPrice"))
        index = f(m.get("indexPrice"))
        funding = f(m.get("lastFundingRate"))
        nt = int(m.get("nextFundingTime") or 0)
        mt = int(m.get("time") or 0)
        close_time = int(t.get("closeTime") or 0)

        if not all(finite(x) for x in (last, openp, high, low, pct, qv, bid, ask, mark, index, funding)):
            missing.append({"symbol": s, "reason": "nonfinite_core_field"})
            continue
        if bid <= 0 or ask <= 0 or ask < bid or last <= 0 or openp <= 0 or index <= 0:
            missing.append({"symbol": s, "reason": "invalid_price_or_book"})
            continue

        spread_bps = (ask - bid) / ((ask + bid) / 2) * 10000
        day_range = (high - low) / openp
        premium = mark / index - 1
        age_ms = max(now_ms - close_time, now_ms - mt)

        reasons = []
        directions = []
        if qv >= 10_000_000 and pct >= 8:
            reasons.append("MOMENTUM_LONG")
            directions.append("LONG")
        if qv >= 10_000_000 and pct <= -8:
            reasons.append("MOMENTUM_SHORT")
            directions.append("SHORT")
        if qv >= 10_000_000 and day_range >= 0.12:
            reasons.append("RANGE_EXPANSION")
        if funding <= -0.003:
            reasons.append("FUNDING_LONG")
            directions.append("LONG")
        if funding >= 0.003:
            reasons.append("FUNDING_SHORT")
            directions.append("SHORT")
        if abs(premium) >= 0.005:
            reasons.append("PREMIUM_STRESS")

        if reasons:
            stage1.append({
                "symbol": s,
                "contractType": meta.get("contractType"),
                "assetClass": "N/A",
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
                "ageMs": age_ms,
                "perpetualFundingSemantics": nt > mt > 0,
            })

    stage1.sort(key=lambda x: (
        max(abs(x["priceChangePercent"]) / 8, abs(x["fundingRatePct"]) / 0.30, abs(x["premiumPct"]) / 0.5, x["dayRangePct"] / 12),
        x["quoteVolume"],
    ), reverse=True)

    audit = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "generatedAtMs": now_ms,
        "source": "Binance official USD-M REST",
        "exchangeInfoRawDeduped": len(dedup),
        "observedContractTypeCounts": contract_counts,
        "validPerpetual": len(valid),
        "excluded": len(dedup) - len(valid),
        "rawEqualsValidPlusExcluded": len(dedup) == len(valid) + (len(dedup) - len(valid)),
        "tickerRaw": len(ticker_by),
        "markRaw": len(mark_by),
        "bookRaw": len(book_by),
        "tickerMatchedValid": len(matched_ticker),
        "markMatchedValid": len(matched_mark),
        "bookMatchedValid": len(matched_book),
        "validWithAllThree": len(set(valid) & set(ticker_by) & set(mark_by) & set(book_by)),
        "missingCoreCount": len(missing),
        "stage1TriggerCount": len(stage1),
        "exclusionReasonCounts": exclusions,
    }
    complete = (
        audit["rawEqualsValidPlusExcluded"]
        and audit["validWithAllThree"] == len(valid)
        and audit["missingCoreCount"] == 0
    )
    out = {
        "schema": "binance-usdm-prefilter-v1",
        "complete": complete,
        "audit": audit,
        "triggers": stage1,
        "missing": missing[:50],
    }
    print("SNAPSHOT_JSON=" + json.dumps(out, separators=(",", ":"), ensure_ascii=False))
    if not complete:
        sys.exit(2)


if __name__ == "__main__":
    main()
