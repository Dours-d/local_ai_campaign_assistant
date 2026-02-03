import requests
import websocket
import json
import time

def run_js(ws, js, req_id=1100):
    msg = json.dumps({"id": req_id, "method": "Runtime.evaluate", "params": {"expression": js, "returnByValue": True, "awaitPromise": True}})
    ws.send(msg)
    while True:
        res = json.loads(ws.recv())
        if res.get('id') == req_id:
            return res.get('result', {}).get('result', {}).get('value')

r = requests.get('http://localhost:9222/json').json()
target = next((t for t in r if 'whydonate.com' in t.get('url', '') and t['type'] == 'page'), None)

if not target:
    print("No Whydonate tab found.")
else:
    ws = websocket.create_connection(target['webSocketDebuggerUrl'])
    
    # Enable Network domain to see what's happening
    ws.send(json.dumps({"id": 1101, "method": "Network.enable"}))
    
    # Give it a few seconds to capture any ongoing background requests
    print("Capturing background network activity for 5 seconds...")
    time.sleep(5)
    
    # Check for any failed resources
    fail_js = """
    (function() {
        const perf = window.performance.getEntriesByType('resource');
        return perf.filter(r => r.nextHopProtocol === '' || r.responseStatus >= 400).map(r => ({
            name: r.name,
            type: r.initiatorType,
            status: r.responseStatus,
            duration: r.duration
        }));
    })()
    """
    failed_requests = run_js(ws, fail_js)
    
    with open('whydonate_network_fails.json', 'w', encoding='utf-8') as f:
        json.dump(failed_requests, f, indent=2)
    
    print(f"Captured {len(failed_requests)} suspicious/failed requests.")
    if failed_requests:
        for fr in failed_requests:
            print(f"- {fr['name']} (Status: {fr['status']})")
