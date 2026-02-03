import requests
import websocket
import json

def run_js(ws, js, req_id=999):
    msg = json.dumps({"id": req_id, "method": "Runtime.evaluate", "params": {"expression": js, "returnByValue": True, "awaitPromise": True}})
    ws.send(msg)
    while True:
        res = json.loads(ws.recv())
        if res.get('id') == req_id:
            return res.get('result', {}).get('result', {}).get('value')

r = requests.get('http://localhost:9222/json').json()
target = next((t for t in r if 'whydonate.com' in t.get('url', '') and t['type'] == 'page'), None)

if not target:
    print("No Whydonate tab found. Please open whydonate.com in Chrome.")
else:
    print(f"Inspecting 'Magic' on: {target['url']}")
    ws = websocket.create_connection(target['webSocketDebuggerUrl'])
    
    # 1. Check cookies for region/country info
    cookies_js = "document.cookie"
    cookies = run_js(ws, cookies_js)
    
    # 2. Check window object for config/environment variables
    # Many Angular/React apps store env config in a global object
    config_js = """
    (function() {
        return {
            windowKeys: Object.keys(window).filter(k => k.includes('CONFIG') || k.includes('ENV') || k.includes('STATE') || k.includes('Why')),
            localStorage: Object.keys(localStorage).filter(k => k.includes('region') || k.includes('country') || k.includes('lang')),
            nav: {
                language: navigator.language,
                languages: navigator.languages,
                onLine: navigator.onLine,
                userAgent: navigator.userAgent
            }
        };
    })()
    """
    config = run_js(ws, config_js)
    
    # 3. Check for specific regional indicators in the body or meta tags
    meta_js = """
    (function() {
        return Array.from(document.querySelectorAll('meta')).map(m => ({name: m.name, content: m.content, property: m.getAttribute('property')}));
    })()
    """
    meta = run_js(ws, meta_js)

    debug_info = {
        "cookies": cookies,
        "config": config,
        "meta": meta
    }
    
    with open('whydonate_magic_debug.json', 'w', encoding='utf-8') as f:
        json.dump(debug_info, f, indent=2)
    
    print("\n'Magic' debug data saved to whydonate_magic_debug.json")
    print(f"Navigator Lang: {config['nav']['language']}")
    print(f"Global Config Keys found: {config['windowKeys']}")
