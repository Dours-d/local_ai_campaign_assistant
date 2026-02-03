import requests
import websocket
import json
import time

def run_js(ws, js, req_id=900):
    msg = json.dumps({"id": req_id, "method": "Runtime.evaluate", "params": {"expression": js, "returnByValue": True, "awaitPromise": True}})
    ws.send(msg)
    while True:
        res = json.loads(ws.recv())
        if res.get('id') == req_id:
            return res.get('result', {}).get('result', {}).get('value')

r = requests.get('http://localhost:9222/json').json()
whydonate_pages = [t for t in r if 'whydonate.com' in t.get('url', '') and t['type'] == 'page']

if not whydonate_pages:
    print("No Whydonate page found.")
else:
    target = whydonate_pages[0]
    print(f"Connecting to: {target['url']}")
    ws = websocket.create_connection(target['webSocketDebuggerUrl'])
    
    # Get HTML
    html = run_js(ws, "document.documentElement.outerHTML")
    with open('whydonate_debug.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("HTML saved to whydonate_debug.html")
    
    # Get all spans and their text
    spans = run_js(ws, "Array.from(document.querySelectorAll('span, button, mat-chip-option')).map(el => ({tag: el.tagName, text: el.innerText.trim(), classes: el.className})).filter(o => o.text.length > 0)")
    with open('whydonate_elements.json', 'w', encoding='utf-8') as f:
        json.dump(spans, f, indent=2)
    print("Elements saved to whydonate_elements.json")
