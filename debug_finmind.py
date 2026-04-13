import os
os.environ['FINMIND_TOKEN'] = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNi0wNC0xMyAwMzoxMTowOCIsInVzZXJfaWQiOiJoc2lhMDczMCIsImVtYWlsIjoicmljaGFyZGhzaWEyMDA0QGdtYWlsLmNvbSIsImlwIjoiMS4xNjUuMTgxLjIyOSJ9.bA_Y5zWsCodVgwRaYlEJvoKTSmKyRTCAJqgxNe_myHI'
os.environ['WATCH_LIST'] = '2330,2454'

from dotenv import load_dotenv
load_dotenv()
token = os.getenv('FINMIND_TOKEN', '')
print("Token loaded:", token[:20] if token else "EMPTY")

from datetime import datetime, timedelta
import requests

WATCH_LIST = ['2330', '2454']
url = 'https://api.finmindtrade.com/api/v4/data'
for days_ago in range(0, 3):
    date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    params = {
        'dataset': 'TaiwanStockPrice',
        'data_id': WATCH_LIST[0],
        'start_date': date,
        'end_date': date,
        'token': token,
    }
    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()
    status = data.get("status")
    print("Date", date, "status=", status)
    print("  data:", data.get("data"))
    if data.get('status') == 200 and data.get('data'):
        rows = data['data']
        print("  rows:", rows)
        if rows:
            latest = rows[-1]
            price = float(latest.get('close', 0))
            print("  Price:", price)
            if price > 0:
                break
