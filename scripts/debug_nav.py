import requests
import json
import websocket
import time

CDP_URL = "http://localhost:9222/json"

def main():
    try:
        r = requests.get(CDP_URL).json()
        target = next(t for t in r if 'whydonate' in t.get('url', '') and t['type'] == 'page')
        ws = websocket.create_connection(target['webSocketDebuggerUrl'])
        ws.settimeout(30)
        
        print(f"Navigating to start...")
        msg = json.dumps({
            "id": 1,
            "method": "Page.navigate",
            "params": {"url": "https://whydonate.com/fundraising/start"}
        })
        ws.send(msg)
        
        while True:
            res = ws.recv()
            data = json.loads(res)
            print(f"Recv: {data.get('method') or data.get('id')}")
            if data.get('id') == 1:
                print("Navigation result received.")
                break
        
        time.sleep(5)
        print("Checking body...")
        msg2 = json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {"expression": "document.body.innerText.substring(0, 100)", "returnByValue": True}
        })
        ws.send(msg2)
        res2 = json.loads(ws.recv())
        print(f"Body: {res2.get('result', {}).get('result', {}).get('value')}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
