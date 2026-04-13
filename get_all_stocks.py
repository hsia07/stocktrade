import requests
import json

# 上市股票列表
r = requests.get('https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_d', timeout=30)
print('Status:', r.status_code)

data = r.json()
print('Total stocks:', len(data))
print('First 3:', data[:3])
