import json
import websocket
import requests
import time

def run_js(ws, js, req_id=100):
    msg = json.dumps({
        "id": req_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": js,
            "returnByValue": True
        }
    })
    ws.send(msg)
    while True:
        res = json.loads(ws.recv())
        if res.get('id') == req_id:
            return res

def main():
    r = requests.get('http://localhost:9222/json').json()
    target = next(t for t in r if t['type'] == 'page' and 'whydonate' in t['url'])
    print(f"Inspecting URL: {target['url']}")
    ws = websocket.create_connection(target['webSocketDebuggerUrl'])
    
    # Try moving to dashboard first to reactivate session
    ws.send(json.dumps({"id": 2, "method": "Page.navigate", "params": {"url": "https://whydonate.com/fundraising/dashboard"}}))
    time.sleep(5)
    ws.send(json.dumps({"id": 3, "method": "Page.navigate", "params": {"url": "https://whydonate.com/fundraising/start"}}))
    time.sleep(5)
    
    js = """
    (function(){
        const chips = Array.from(document.querySelectorAll('mat-chip-option, .category-chip, .mat-mdc-chip')).map(c => c.innerText.trim());
        const spans = Array.from(document.querySelectorAll('span')).map(s => s.innerText.trim()).filter(t => t.length > 5);
        const btn = document.getElementById('saveStep1');
        const cats = !!document.querySelector('.categories-options');
        const errors = Array.from(document.querySelectorAll('mat-error')).map(e => e.innerText);
        
        return {
            url: window.location.href,
            has_categories: cats,
            chips: chips,
            spans_sample: spans.slice(0, 20),
            errors: errors,
            btn: btn ? {
                disabled: btn.disabled,
                classes: btn.className
            } : "NOT_FOUND",
            body_text: document.body.innerText.substring(0, 1000)
        };
    })()
    """
    print(json.dumps(run_js(ws, js), indent=2))

if __name__ == "__main__":
    main()
