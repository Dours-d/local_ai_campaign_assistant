import requests
import json
import websocket
import time

CDP_URL = "http://localhost:9222/json"

def run_js(ws, js):
    msg_id = int(time.time() * 1000)
    ws.send(json.dumps({"id": msg_id, "method": "Runtime.evaluate", "params": {"expression": js, "returnByValue": True}}))
    while True:
        res = json.loads(ws.recv())
        if res.get('id') == msg_id:
            return res.get('result', {}).get('result', {}).get('value')

def main():
    try:
        r = requests.get(CDP_URL).json()
        target = None
        for t in r:
            if 'whydonate.com/dashboard' in t.get('url', '') and t['type'] == 'page':
                target = t
                break
        
        if not target:
            print("No Whydonate Dashboard tab found. Please open it.")
            return

        ws = websocket.create_connection(target['webSocketDebuggerUrl'])
        ws.settimeout(10)
        
        print(f"Scraping titles from {target['url']}...")
        
        # Click "View More" until it's gone or we reach a limit
        for i in range(30):
            print(f"Scroll and load more {i+1}...")
            run_js(ws, "window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            btn_clicked = run_js(ws, """
                (function() {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const viewMore = btns.find(b => b.innerText.includes('View more') || b.innerText.includes('Toon meer'));
                    if (viewMore && !viewMore.disabled) {
                        viewMore.click();
                        return true;
                    }
                    return false;
                })()
            """)
            if not btn_clicked:
                # Check if it's still loading
                if run_js(ws, "document.body.innerText.includes('Loading')"):
                    time.sleep(2)
                    continue
                break 
        
        # More specific title selector
        titles = run_js(ws, """
            (function() {
                const results = [];
                // Target card titles specifically
                document.querySelectorAll('mat-card-title').forEach(el => results.push(el.innerText.trim()));
                // Fallback for list view
                document.querySelectorAll('.title-text, h3').forEach(el => results.push(el.innerText.trim()));
                return results;
            })()
        """)
        
        if not titles: # Fallback if JS array method failed
            titles = run_js(ws, "Array.from(document.querySelectorAll('mat-card-title, .title-text, h3')).map(el => el.innerText.trim())")
        
        unique_titles = list(set([t for t in titles if len(t) > 5]))
        print(f"Found {len(unique_titles)} unique titles.")
        
        with open('data/whydonate_all_campaigns.json', 'w', encoding='utf-8') as f:
            json.dump([{"title": t} for t in unique_titles], f, indent=2)
            
        print("Updated data/whydonate_all_campaigns.json")
        ws.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
