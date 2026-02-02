
import requests
import json
import websocket

CDP_URL = "http://localhost:9222/json"

def main():
    r = requests.get(CDP_URL).json()
    t = [p for p in r if 'fundraising/start' in p.get('url', '')][0]
    ws = websocket.create_connection(t['webSocketDebuggerUrl'])
    
    # Just type directly "Netherlands" and blur
    js = """
    (function() {
        const address = document.getElementById('mat-input-0');
        address.focus();
        address.value = "Netherlands";
        address.dispatchEvent(new Event('input', { bubbles: true }));
        address.dispatchEvent(new Event('change', { bubbles: true }));
        address.blur();
        
        // Find category by click again
        const elements = Array.from(document.querySelectorAll('*'));
        const humanitarian = elements.find(el => el.innerText === "Humanitarian Aid" && el.tagName !== "SCRIPT");
        if (humanitarian) humanitarian.click();

        return "FORCED_INPUT";
    })()
    """
    ws.send(json.dumps({'id':1, 'method':'Runtime.evaluate', 'params':{'expression':js, 'returnByValue':True}}))
    print(json.loads(ws.recv())['result']['result']['value'])
    ws.close()

if __name__ == "__main__":
    main()
