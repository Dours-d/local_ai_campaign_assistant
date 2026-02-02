
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
        const address = document.getElementById('mat-input-0');
        const nextBtn = document.getElementById('saveStep1');
        const humanitarianAid = Array.from(document.querySelectorAll('div, span, p')).find(el => el.innerText === "Humanitarian Aid");
        
        return {
            address_value: address ? address.value : "NOT_FOUND",
            next_disabled: nextBtn ? nextBtn.disabled : "NOT_FOUND",
            humanitarian_selected: humanitarianAid ? humanitarianAid.closest('.category-card')?.classList.contains('selected') : "NOT_FOUND"
        };
    })()
    """
    ws.send(json.dumps({'id':1, 'method':'Runtime.evaluate', 'params':{'expression':js, 'returnByValue':True}}))
    print(json.dumps(json.loads(ws.recv())['result']['result']['value'], indent=2))
    ws.close()

if __name__ == "__main__":
    main()
