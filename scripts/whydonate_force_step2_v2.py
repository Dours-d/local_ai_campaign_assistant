
import requests
import json
import websocket
import time

CDP_URL = "http://localhost:9222/json"

def main():
    r = requests.get(CDP_URL).json()
    t = [p for p in r if p.get('url') == 'https://whydonate.com/fundraising/start'][0]
    ws = websocket.create_connection(t['webSocketDebuggerUrl'])
    
    # Force click "Someone Else" again, maybe it needs a specific target
    js = """
    (function() {
        const els = Array.from(document.querySelectorAll('*'));
        const candidates = els.filter(el => el.innerText === "Someone Else" || el.innerText === "Iemand anders");
        
        let clicked = false;
        // Try clicking the card wrapper if possible
        for (let el of candidates) {
             const card = el.closest('.fundraiser-type-card') || el.closest('div[role="button"]');
             if (card) {
                 card.click();
                 clicked = true;
                 break;
             }
        }
        
        // If no card found, click text itself
        if (!clicked && candidates.length > 0) {
            candidates[0].click();
            clicked = true;
        }
        
        return clicked ? "CLICKED" : "NOT_FOUND";
    })()
    """
    ws.send(json.dumps({'id':1, 'method':'Runtime.evaluate', 'params':{'expression':js, 'returnByValue':True}}))
    print(f"Click status: {json.loads(ws.recv())['result']['result']['value']}")
    
    time.sleep(2)
    
    # Check if we moved
    js_check = "document.querySelector('input[placeholder*=\"Title\"]') ? 'MOVED' : 'STILL_HERE'"
    ws.send(json.dumps({'id':2, 'method':'Runtime.evaluate', 'params':{'expression':js_check, 'returnByValue':True}}))
    print(f"Status: {json.loads(ws.recv())['result']['result']['value']}")
    
    ws.close()

if __name__ == "__main__":
    main()
