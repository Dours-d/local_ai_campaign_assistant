
import requests
import json
import websocket

CDP_URL = "http://localhost:9222/json"

def main():
    r = requests.get(CDP_URL).json()
    t = [p for p in r if p.get('url') == 'https://whydonate.com/fundraising/start'][0]
    ws = websocket.create_connection(t['webSocketDebuggerUrl'])
    
    js = """
    (function() {
        const els = document.querySelectorAll('*');
        const candidates = [];
        els.forEach(el => {
            if (el.innerText === "Someone Else" || el.innerText === "Iemand anders") {
                candidates.push(el);
            }
        });
        
        if (candidates.length > 0) {
            candidates[0].click();
            return "CLICKED_CANDIDATE";
        }
        return "NO_CANDIDATES";
    })()
    """
    ws.send(json.dumps({'id':1, 'method':'Runtime.evaluate', 'params':{'expression':js, 'returnByValue':True}}))
    print(json.dumps(json.loads(ws.recv())['result']['result']['value'], indent=2))
    ws.close()

if __name__ == "__main__":
    main()
