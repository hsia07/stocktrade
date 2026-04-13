import requests
import json

r = requests.get('http://localhost:8765/api/state')
d = r.json()

# Check backtest agent
agents = d.get('agents', {})
bt = agents.get('backtest_2330')

with open('debug_output.txt', 'w', encoding='utf-8') as f:
    if bt:
        f.write(f"backtest_2330 exists: {json.dumps(bt, ensure_ascii=False)[:500]}\n")
    else:
        f.write("backtest_2330 is None\n")
    
    # Check all agent keys containing 'back'
    back_keys = [k for k in agents.keys() if 'back' in k]
    f.write(f"Keys with 'back': {back_keys[:10]}\n")
    
    # Check selected symbol
    f.write(f"Current state keys: {list(d.keys())[:20]}\n")
