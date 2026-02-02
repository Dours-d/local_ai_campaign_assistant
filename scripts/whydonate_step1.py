
import requests
import json
import websocket
import time

CDP_URL = "http://localhost:9222/json"

def main():
    r = requests.get(CDP_URL).json()
    t = [p for p in r if p.get('url') == 'https://whydonate.com/fundraising/start'][0]
    ws = websocket.create_connection(t['webSocketDebuggerUrl'])
    
    js = """
    (function() {
        // 1. Find the Humanitarian Aid category specifically by its text and parent
        const elements = Array.from(document.querySelectorAll('*'));
        const humanitarian = elements.find(el => el.innerText === "Humanitarian Aid" && el.tagName !== "SCRIPT");
        
        if (humanitarian) {
            humanitarian.click();
            // Sometimes it's a bubble/card around it
            const card = humanitarian.closest('.category-card') || humanitarian.closest('div[role="button"]');
            if (card) card.click();
        }
        
        // 2. Clear and re-type address to trigger potential autocomplete
        const address = document.getElementById('mat-input-0');
        if (address) {
            address.focus();
            address.value = "Netherlands";
            address.dispatchEvent(new Event('input', { bubbles: true }));
            address.dispatchEvent(new Event('change', { bubbles: true }));
        }
        
        return "CLICKED_CATEGORY";
    })()
    """
    ws.send(json.dumps({'id':1, 'method':'Runtime.evaluate', 'params':{'expression':js, 'returnByValue':True}}))
    print(json.loads(ws.recv())['result']['result']['value'])
    
    time.sleep(2)
    
    # Check if "Next" is enabled now
    js_check = 'document.getElementById("saveStep1").disabled'
    ws.send(json.dumps({'id':2, 'method':'Runtime.evaluate', 'params':{'expression':js_check, 'returnByValue':True}}))
    disabled = json.loads(ws.recv())['result']['result']['value']
    print(f"Next Disabled: {disabled}")
    
    if not disabled:
        ws.send(json.dumps({'id':3, 'method':'Runtime.evaluate', 'params':{'expression':'document.getElementById("saveStep1").click()', 'returnByValue':True}}))
        print("Clicked Next")
        
    ws.close()

if __name__ == "__main__":
    main()
