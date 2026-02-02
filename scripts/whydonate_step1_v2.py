
import requests
import json
import websocket
import time

CDP_URL = "http://localhost:9222/json"

def main():
    try:
        r = requests.get(CDP_URL).json()
        t = [p for p in r if 'fundraising/start' in p.get('url', '')][0]
        ws = websocket.create_connection(t['webSocketDebuggerUrl'])
        
        js = """
        (async function() {
            // 1. Select Category
            const elements = Array.from(document.querySelectorAll('*'));
            const humanitarian = elements.find(el => el.innerText === "Humanitarian Aid" && el.tagName !== "SCRIPT");
            if (humanitarian) {
                humanitarian.click();
                const card = humanitarian.closest('.category-card');
                if (card) card.click();
            }
            
            // 2. Focus and Type Address
            const address = document.getElementById('mat-input-0');
            if (address) {
                address.focus();
                address.value = ""; // Clear first
                address.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Type "Amsterdam" char by char to trigger autocomplete
                const text = "Amsterdam";
                address.value = text;
                address.dispatchEvent(new Event('input', { bubbles: true }));
                address.dispatchEvent(new Event('keydown', { bubbles: true }));
                address.dispatchEvent(new Event('keyup', { bubbles: true }));
            }
            
            return "TYPED_ADDRESS";
        })()
        """
        ws.send(json.dumps({'id':1, 'method':'Runtime.evaluate', 'params':{'expression':js, 'returnByValue':True, 'awaitPromise':True}}))
        print(json.loads(ws.recv())['result']['result']['value'])
        
        time.sleep(3) # Wait for suggestions
        
        # Check for suggestions and click
        js_click = """
        (function() {
            const options = document.querySelectorAll('.mat-option, .pac-item');
            if (options.length > 0) {
                options[0].click();
                return "CLICKED_OPTION";
            }
            return "NO_OPTIONS_FOUND";
        })()
        """
        ws.send(json.dumps({'id':2, 'method':'Runtime.evaluate', 'params':{'expression':js_click, 'returnByValue':True}}))
        res = json.loads(ws.recv())
        print(f"Option selection: {res['result']['result']['value']}")
        
        time.sleep(1)
        
        # Check Next Button
        js_check = 'document.getElementById("saveStep1").disabled'
        ws.send(json.dumps({'id':3, 'method':'Runtime.evaluate', 'params':{'expression':js_check, 'returnByValue':True}}))
        disabled = json.loads(ws.recv())['result']['result']['value']
        print(f"Next Disabled: {disabled}")
        
        if not disabled:
            ws.send(json.dumps({'id':4, 'method':'Runtime.evaluate', 'params':{'expression':'document.getElementById("saveStep1").click()', 'returnByValue':True}}))
            print("Clicked Next")
            
        ws.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
