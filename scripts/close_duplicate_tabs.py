import requests
import json

r = requests.get('http://localhost:9222/json').json()
whydonate_pages = [t for t in r if ('whydonate.com' in t.get('url', '')) and t['type'] == 'page']

if len(whydonate_pages) > 1:
    print(f"Found {len(whydonate_pages)} Whydonate tabs. Closing all but the first one.")
    for t in whydonate_pages[1:]:
        target_id = t['id']
        requests.get(f"http://localhost:9222/json/close/{target_id}")
        print(f"Closed: {target_id} | {t['url']}")
else:
    print("Only one or zero Whydonate tabs found.")
