
import requests
import json
try:
    r = requests.get('http://localhost:9222/json').json()
    for t in r:
        if t.get('type') == 'page':
            print(f"{t.get('url')} | {t.get('title')}")
except Exception as e:
    print(f"Error: {e}")
