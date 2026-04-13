import twstock
twstock.__update_codes()
stocks = [c for c in twstock.codes.keys() if len(c) == 4 and c.isdigit()]
print(f"Total: {len(stocks)} stocks")

# Request in small batches
count = 0
for i in range(0, min(50, len(stocks)), 10):
    batch = stocks[i:i+10]
    try:
        result = twstock.realtime.get(batch)
        for code, data in result.items():
            if isinstance(data, dict):
                price = data.get("realtime", {}).get("latest_trade_price", "-")
                if price and price not in ["-", "", None]:
                    count += 1
                    print(f"{code}: {price}")
                    if count >= 20:
                        break
    except Exception as e:
        print(f"Error at {i}: {e}")
    if count >= 20:
        break
print(f"Total with prices: {count}")
