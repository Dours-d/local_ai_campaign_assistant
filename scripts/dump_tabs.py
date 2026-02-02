
import requests
import json
r = requests.get('http://localhost:9222/json').json()
for t in r:
    print(f"{t.get('title')} | {t.get('url')} | {t.get('type')}")
