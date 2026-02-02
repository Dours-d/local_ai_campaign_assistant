
import requests
import json
import websocket

CDP_URL = "http://localhost:9222/json"

def main():
    r = requests.get(CDP_URL).json()
    t = [p for p in r if 'fundraising/start' in p.get('url', '')][0]
    ws = websocket.create_connection(t['webSocketDebuggerUrl'])
    
    js = """
    (function() {
        // Just enable the button manually and click it
        const btn = document.getElementById('saveStep1');
        btn.disabled = false;
        btn.click();
        return "CLICKED_FORCE_ENABLE";
    })()
    """
    ws.send(json.dumps({'id':1, 'method':'Runtime.evaluate', 'params':{'expression':js, 'returnByValue':True}}))
    print(json.loads(ws.recv())['result']['result']['value'])
    ws.close()

if __name__ == "__main__":
    main()
