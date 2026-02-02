
import requests
import json
import websocket

CDP_URL = "http://localhost:9222/json"

def main():
    try:
        r = requests.get(CDP_URL).json()
        pages = [t for t in r if t.get('type') == 'page' and 'whydonate.com' in t.get('url', '')]
        
        for page in pages:
            print(f"Deep Scanning: {page['url']} ({page['id']})")
            try:
                ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=5)
                # Script to find inputs even in shadow DOMs
                js = """
                (function() {
                    const found = [];
                    function scan(root) {
                        if (!root) return;
                        root.querySelectorAll('input, textarea, select, button').forEach(el => {
                            found.push({
                                tag: el.tagName,
                                name: el.name || el.getAttribute('name'),
                                id: el.id,
                                placeholder: el.placeholder || el.getAttribute('placeholder'),
                                text: el.innerText
                            });
                        });
                        root.querySelectorAll('*').forEach(el => {
                            if (el.shadowRoot) scan(el.shadowRoot);
                        });
                    }
                    scan(document);
                    return found;
                })()
                """
                msg = json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": js, "returnByValue": True}})
                ws.send(msg)
                res = json.loads(ws.recv())
                value = res.get('result', {}).get('result', {}).get('value')
                if value and len(value) > 3:
                    print(f"FORM_DETECTED on {page['url']}")
                    print(json.dumps(value, indent=2))
                    ws.close()
                    return
                ws.close()
            except:
                pass
        print("TOTAL_FAILURE")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
