
import requests
import json
import time

CDP_URL = "http://localhost:9222/json"

def get_tabs():
    try:
        r = requests.get(CDP_URL)
        return r.json()
    except:
        return []

def open_tab(url):
    try:
        requests.put(f"{CDP_URL}/new?{url}")
        print(f"Opened/Navigated tab: {url}")
    except Exception as e:
        print(f"Failed to open tab: {e}")

tabs = get_tabs()
wd_tab = next((t for t in tabs if "whydonate" in t.get("url", "")), None)

if wd_tab:
    print(f"Current Whydonate Tab: {wd_tab['title']} - {wd_tab['url']}")
    # If not on creation page, navigate there
    if "fundraising-for/new" not in wd_tab['url']:
        print("Navigating to creation page...")
        open_tab("https://whydonate.com/en/fundraising-for/new")
else:
    print("No Whydonate tab. Opening creation page...")
    open_tab("https://whydonate.com/en/fundraising-for/new")
