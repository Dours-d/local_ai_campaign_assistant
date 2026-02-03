import requests
import websocket
import json

r = requests.get('http://localhost:9222/json').json()
target = next(t for t in r if t['type'] == 'page' and 'whydonate' in t['url'])
ws = websocket.create_connection(target['webSocketDebuggerUrl'])

def run_js(ws, js, req_id=500):
    msg = json.dumps({"id": req_id, "method": "Runtime.evaluate", "params": {"expression": js, "returnByValue": True}})
    ws.send(msg)
    while True:
        res = json.loads(ws.recv())
        if res.get('id') == req_id:
            return res.get('result', {}).get('result', {}).get('value')

js = 'Array.from(document.querySelectorAll("a, button")).find(a => (a.innerText || "").includes("Start Fundraiser"))?.href || "NOT_FOUND"'
print(f"Start Fundraiser Link: {run_js(ws, js)}")

js_cats = 'Array.from(document.querySelectorAll("mat-chip-option")).map(c => c.innerText.trim())'
print("Chips text:")
print(json.dumps(run_js(ws, js_cats), indent=2))
