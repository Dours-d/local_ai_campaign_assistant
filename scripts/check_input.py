
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
        const results = [];
        document.querySelectorAll('input, select, textarea').forEach(input => {
            let label = "";
            if (input.id) {
                const labelEl = document.querySelector(`label[for="${input.id}"]`);
                if (labelEl) label = labelEl.innerText;
            }
            if (!label) label = input.closest('div')?.innerText.split('\\n')[0];
            results.push({ label, id: input.id, name: input.name, type: input.type });
        });
        return results;
    })()
    """
    ws.send(json.dumps({'id':1, 'method':'Runtime.evaluate', 'params':{'expression':js, 'returnByValue':True}}))
    data = json.loads(ws.recv())['result']['result']['value']
    print(json.dumps(data, indent=2))
    ws.close()

if __name__ == "__main__":
    main()
