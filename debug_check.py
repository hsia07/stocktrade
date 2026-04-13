import requests
r = requests.get('http://localhost:8765/api/state')
d = r.json()
print("ticks:", d.get('ticks', {}))
print("real_data keys:", list(d.get('ticks', {}).keys())[:10])
