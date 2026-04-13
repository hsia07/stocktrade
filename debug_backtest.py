import requests
r = requests.get('http://localhost:8765/api/state')
d = r.json()
agents = d.get('agents', {})
keys = list(agents.keys())
print('Agent keys:', keys[:20])
for k in keys:
    if 'back' in k:
        print(f'{k}: {agents[k]}')
