import requests
import json
url = 'https://mis.twse.com.tw/stock/api/getStockInfo.jsp'
params = {'ex_ch': 'tse_2330.tw|tse_2454.tw|tse_2317.tw|tse_2308.tw', 'json': 1, 'delay': 0}
r = requests.get(url, params=params, timeout=10)
data = json.loads(r.text)
for item in data.get('msgArray', []):
    print(f"{item['c']}: {item['z']}")
