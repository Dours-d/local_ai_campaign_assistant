
import requests
import time

url = "http://localhost:9222/json"

for i in range(5):
    try:
        r = requests.get(url, timeout=3)
        data = r.json()
        print(f"Attempt {i+1}: Found {len(data)} items")
        for t in data:
            print(f"  {t.get('type')}: {t.get('url')}")
        if len(data) > 2:
            break
    except Exception as e:
        print(f"Attempt {i+1}: {e}")
    time.sleep(2)
