import requests
r = requests.get('http://localhost:8765/api/state')
d = r.json()
ticks = d.get('ticks', {})
for sym, tick in ticks.items():
    print(f"{sym}: {tick['price']}")
