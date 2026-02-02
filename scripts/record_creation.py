
import requests
import json
import websocket
import time
import os

CDP_URL = "http://localhost:9222/json"
LOG_FILE = "data/whydonate_creation_log.json"

def get_page():
    try:
        r = requests.get(CDP_URL).json()
        return next((p for p in r if 'whydonate.com' in p.get('url', '') and p.get('type') == 'page'), None)
    except:
        return None

def scan_page(ws):
    js = """
    (function() {
        const state = {
            url: window.location.href,
            inputs: [],
            buttons: [],
            visible_text: document.body.innerText.substring(0, 200)
        };
        
        document.querySelectorAll('input, textarea, select').forEach(el => {
            state.inputs.push({
                tag: el.tagName,
                id: el.id,
                name: el.name,
                type: el.type,
                placeholder: el.placeholder,
                value: el.value,
                visible: el.offsetParent !== null
            });
        });
        
        document.querySelectorAll('button').forEach(el => {
             state.buttons.push({
                text: el.innerText,
                id: el.id,
                class: el.className,
                disabled: el.disabled
             });
        });
        
        return state;
    })()
    """
    ws.send(json.dumps({'id': int(time.time()), 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    return res.get('result', {}).get('result', {}).get('value')

def main():
    print("Recording started. Please create the campaign in Chrome...")
    history = []
    
    last_url = ""
    
    # Run for 5 minutes or untill stopped
    for i in range(100):
        page = get_page()
        if page:
            try:
                ws = websocket.create_connection(page['webSocketDebuggerUrl'])
                state = scan_page(ws)
                ws.close()
                
                if state:
                    # Only log if something changed or every 5th poll
                    if state['url'] != last_url or i % 5 == 0:
                        print(f"[{time.strftime('%H:%M:%S')}] On {state['url']}")
                        last_url = state['url']
                        history.append({'timestamp': time.time(), 'state': state})
                        
                        # Save incrementally
                        with open(LOG_FILE, 'w') as f:
                            json.dump(history, f, indent=2)
            except Exception as e:
                print(f"Error scanning: {e}")
        
        time.sleep(3)

if __name__ == "__main__":
    main()
