
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
        // Try to verify if we moved to next step or if a modal opened
        // Looking for "Title" input which should be in the next step
        const titleInput = document.querySelector('input[name="title"], input[placeholder*="Title"]');
        if (titleInput) return "TITLE_INPUT_FOUND";
        
        // Check if we are still on Step 2 (Selector)
        const someone = Array.from(document.querySelectorAll('*')).find(el => el.innerText === "Someone Else");
        if (someone) return "STILL_ON_STEP_2";
        
        return "UNKNOWN_STATE";
    })()
    """
    ws.send(json.dumps({'id':1, 'method':'Runtime.evaluate', 'params':{'expression':js, 'returnByValue':True}}))
    print(json.dumps(json.loads(ws.recv())['result']['result']['value'], indent=2))
    ws.close()

if __name__ == "__main__":
    main()
