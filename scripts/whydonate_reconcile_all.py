import requests
import json
import websocket
import time
import os

CDP_URL = "http://localhost:9222/json"

MSG_ID = 1

def normalize_title(t):
    import re
    if not t: return ""
    t = str(t).replace('\u00a0', ' ').lower()
    t = re.sub(r'[^a-z0-9 ]', '', t)
    return " ".join(t.split())

def run_js(ws, js, timeout=60):
    global MSG_ID
    MSG_ID += 1
    this_id = MSG_ID
    msg = json.dumps({
        "id": this_id,
        "method": "Runtime.evaluate",
        "params": {"expression": js, "returnByValue": True, "awaitPromise": True}
    })
    ws.send(msg)
    start_t = time.time()
    while time.time() - start_t < timeout:
        try:
            res = json.loads(ws.recv())
            if res.get('id') == this_id:
                return res.get('result', {}).get('result', {}).get('value')
        except: continue
    return None

def main():
    try:
        r = requests.get(CDP_URL).json()
        target = next((t for t in r if 'whydonate.com/dashboard' in t.get('url', '') and t['type'] == 'page'), None)
        
        if not target:
            print("Dashboard not found. Opening...")
            requests.put(f"{CDP_URL}/new?https://whydonate.com/dashboard")
            time.sleep(8)
            r = requests.get(CDP_URL).json()
            target = next((t for t in r if 'whydonate.com/dashboard' in t.get('url', '') and t['type'] == 'page'), None)

        ws = websocket.create_connection(target['webSocketDebuggerUrl'])
        ws.settimeout(60)
        
        print("Gathering all active Whydonate campaigns (Title + URL)...")
        
        # Scroll and Load All
        for i in range(30):
            run_js(ws, "window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            btn_clicked = run_js(ws, """
                (function() {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const viewMore = btns.find(b => b.innerText.includes('View more') || b.innerText.includes('Toon meer'));
                    if (viewMore && !viewMore.disabled) {
                        viewMore.click(); return true;
                    }
                    return false;
                })()
            """)
            if not btn_clicked: break

        # Scrape titles and relative paths
        print("Scraping cards...")
        # Wait for cards to appear
        for _ in range(10):
            has_cards = run_js(ws, "!!document.querySelector('mat-card-title')")
            if has_cards: break
            time.sleep(2)

        data = run_js(ws, """
            Array.from(document.querySelectorAll('mat-card, .fundraising-card, .campaign-card')).map(card => {
                const titleEl = card.querySelector('mat-card-title') || card.querySelector('.title-text') || card.querySelector('h3');
                const linkEl = card.querySelector('a[href*="/fundraising/"]');
                if (titleEl && linkEl) {
                    return {
                        title: titleEl.innerText.trim(),
                        url: linkEl.href
                    };
                }
                return null;
            }).filter(x => x !== null)
        """)
        
        if not data:
            print("No data found with mat-card. Trying generic link extraction...")
            data = run_js(ws, """
                Array.from(document.querySelectorAll('a[href*="/fundraising/"]'))
                    .map(a => ({ title: a.innerText.trim(), url: a.href }))
                    .filter(x => x.title.length > 5)
            """)

        print(f"Actually found {len(data)} campaigns on dashboard.")
        
        # Save raw mapping for safety
        with open('data/whydonate_scrape_full.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        # Reconcile with Unified DB
        unified_path = 'data/campaigns_unified.json'
        if os.path.exists(unified_path):
            with open(unified_path, 'r', encoding='utf-8') as f:
                unified_data = json.load(f)
            
            # Extract list from dict if needed
            campaigns_list = unified_data.get('campaigns', []) if isinstance(unified_data, dict) else unified_data
            
            # Map by normalized title
            wd_map = {normalize_title(item['title']): item['url'] for item in data}
            
            updated_count = 0
            for camp in campaigns_list:
                norm = normalize_title(camp.get('title', ''))
                if norm in wd_map:
                    # Update or add Whydonate info
                    if 'whydonate' not in camp:
                        camp['whydonate'] = {}
                    camp['whydonate']['url'] = wd_map[norm]
                    camp['whydonate']['status'] = 'active'
                    updated_count += 1
            
            with open(unified_path, 'w', encoding='utf-8') as f:
                json.dump(unified_data, f, indent=2)
            print(f"Reconciliation complete. Updated {updated_count} records in unified database.")
        
        ws.close()
    except Exception as e:
        print(f"Reconciliation Error: {e}")

if __name__ == "__main__":
    main()
