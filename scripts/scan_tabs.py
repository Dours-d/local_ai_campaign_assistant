
import requests
import json
import websocket

CDP_URL = "http://localhost:9222/json"

def main():
    try:
        r = requests.get(CDP_URL).json()
        found_any = False
        for t in r:
            if t.get('type') == 'page' and 'whydonate' in t.get('url', ''):
                try:
                    ws = websocket.create_connection(t['webSocketDebuggerUrl'], timeout=2)
                    # Look for title input or goal input
                    js = 'document.querySelector("input[name=\'title\'], input[placeholder*=\'Title\'], input[placeholder*=\'Naam\']") ? "FORM_VISIBLE" : "NO_FORM"'
                    msg = json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": js, "returnByValue": True}})
                    ws.send(msg)
                    res = json.loads(ws.recv())
                    val = res.get('result', {}).get('result', {}).get('value')
                    print(f"{t['url']} | {val} | {t['id']}")
                    found_any = True
                    ws.close()
                except:
                    pass
        if not found_any:
            print("NO_WHYDONATE_TABS")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
