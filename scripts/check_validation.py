
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
        const results = [];
        document.querySelectorAll('input, select, textarea').forEach(el => {
            const field = el.closest('.mat-form-field');
            const error = field ? field.querySelector('.mat-error')?.innerText : "";
            results.push({
                placeholder: el.placeholder,
                id: el.id,
                value: el.value,
                error: error,
                visible: el.offsetParent !== null
            });
        });
        
        const selectedCategory = document.querySelector('.category-card.selected, .selected-category')?.innerText;
        
        return { inputs: results, selectedCategory };
    })()
    """
    ws.send(json.dumps({'id':1, 'method':'Runtime.evaluate', 'params':{'expression':js, 'returnByValue':True}}))
    print(json.dumps(json.loads(ws.recv())['result']['result']['value'], indent=2))
    ws.close()

if __name__ == "__main__":
    main()
