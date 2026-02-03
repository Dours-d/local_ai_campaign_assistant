import requests
import json
import websocket

CDP_URL = "http://localhost:9222/json"

def main():
    try:
        r = requests.get(CDP_URL).json()
        target = next((t for t in r if 'whydonate.com/dashboard' in t.get('url', '')), None)
        if not target:
            print("No dashboard found")
            return
        
        ws = websocket.create_connection(target['webSocketDebuggerUrl'])
        js = "document.body.innerText.includes('Login') || document.body.innerText.includes('Aanmelden')"
        ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
        res = json.loads(ws.recv())
        logged_out = res['result']['result']['value']
        print(f"Logged out: {logged_out}")
        ws.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
