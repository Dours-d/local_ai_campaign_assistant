
import requests
import json

CDP_URL = "http://localhost:9222/json"

def main():
    try:
        r = requests.get(CDP_URL)
        tabs = r.json()
        for t in tabs:
            if t.get('type') == 'page' and 'whydonate.com/fundraising' in t.get('url', ''):
                print(f"ID:{t['id']}")
                print(f"URL:{t['url']}")
                return
        print("NOT_FOUND")
    except Exception as e:
        print(f"ERROR:{e}")

if __name__ == "__main__":
    main()
