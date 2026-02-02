
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
        // Look for Step 2 elements ("Myself", "Someone Else", "Organization")
        const cards = Array.from(document.querySelectorAll('.fundraiser-type-card, div[role="button"]'));
        const options = cards.map(c => c.innerText.split('\\n')[0]);
        
        let found = "NO_OPTIONS_FOUND";
        
        // Try to click "Someone Else"
        const someoneElse = cards.find(c => c.innerText.includes("Someone Else") || c.innerText.includes("Someone else"));
        if (someoneElse) {
            someoneElse.click();
            found = "CLICKED_SOMEONE_ELSE";
        }
        
        return { options, action: found };
    })()
    """
    ws.send(json.dumps({'id':1, 'method':'Runtime.evaluate', 'params':{'expression':js, 'returnByValue':True}}))
    print(json.dumps(json.loads(ws.recv())['result']['result']['value'], indent=2))
    ws.close()

if __name__ == "__main__":
    main()
