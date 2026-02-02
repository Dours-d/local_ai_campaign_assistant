
import requests
import json
import websocket
import time
import os

CDP_URL = "http://localhost:9222/json"

CAMPAIGN = {
    "title": "Help Marah and her family rebuild their lives, Palestine.",
    "image_path": r"C:\Users\gaelf\Pictures\GAZA\Marah Ahmad Magde\WhatsApp Image 2025-05-02 à 12.32.25_19f2b6f1.jpg"
}

def get_socket():
    try:
        r = requests.get(CDP_URL).json()
        for t in r:
            if 'whydonate.com' in t.get('url', '') and t['type'] == 'page':
                return websocket.create_connection(t['webSocketDebuggerUrl'])
        return None
    except:
        return None

def run_js(ws, js):
    msg = json.dumps({
        "id": int(time.time() * 1000),
        "method": "Runtime.evaluate",
        "params": {
            "expression": js,
            "returnByValue": True,
            "awaitPromise": True
        }
    })
    ws.send(msg)
    while True:
        res = json.loads(ws.recv())
        if res.get('id') == json.loads(msg)['id']:
            val = res.get('result', {}).get('result', {}).get('value')
            if not val:
                 val = res.get('result', {}).get('result', {}).get('description')
            return val

def main():
    print(f"Creating: {CAMPAIGN['title']}")
    ws = get_socket()
    if not ws:
        print("No tab found.")
        return

    # STEP 1: Category & Location
    print("Step 1...")
    js1 = """
    (async function() {
        const h = Array.from(document.querySelectorAll('*')).find(el => el.innerText === "Humanitarian Aid");
        if (h) h.click();
        
        await new Promise(r => setTimeout(r, 500));
        
        const addr = document.getElementById('mat-input-0');
        if (addr) {
            addr.value = "Netherlands";
            addr.dispatchEvent(new Event('input', {bubbles:true}));
        }
        
        await new Promise(r => setTimeout(r, 1000));
        
        const btn = document.getElementById('saveStep1');
        if (btn) {
            btn.disabled = false;
            btn.click();
            return "NEXT_CLICKED";
        }
        return "BTN_MISSING";
    })()
    """
    print(run_js(ws, js1))
    time.sleep(4)

    # STEP 2: Myself
    print("Step 2 (Myself)...")
    js2 = """
    (async function() {
        const els = Array.from(document.querySelectorAll('.fundraiser-type-card, div[role="button"]'));
        const myself = els.find(el => el.innerText.includes("Myself") || el.innerText.includes("Me") || el.innerText.includes("Mijzelf"));
        if (myself) {
            myself.click();
            return "CLICKED_MYSELF";
        }
        return "MYSELF_NOT_FOUND";
    })()
    """
    print(run_js(ws, js2))
    time.sleep(4)

    # STEP 3: Title & Image
    print("Step 3 (Details)...")
    js3 = f"""
    (function() {{
        const t = document.querySelector('input[placeholder*="Title"]');
        if (t) {{
            t.value = {json.dumps(CAMPAIGN['title'])};
            t.dispatchEvent(new Event('input', {{bubbles:true}}));
            return "TITLE_SET";
        }}
        return "TITLE_NOT_FOUND";
    }})()
    """
    print(run_js(ws, js3))

    # Image
    print("Uploading Image...")
    try:
        doc_msg = json.dumps({"id": 600, "method": "DOM.getDocument"})
        ws.send(doc_msg)
        root = json.loads(ws.recv())['result']['root']
        node_msg = json.dumps({
            "id": 601, 
            "method": "DOM.querySelector", 
            "params": {
                "nodeId": root['nodeId'], 
                "selector": "input[type='file']"
            }
        })
        ws.send(node_msg)
        node_res = json.loads(ws.recv())
        
        if 'nodeId' in node_res.get('result', {}):
            nid = node_res['result']['nodeId']
            run_js(ws, "document.querySelector('input[type=\"file\"]').style.display='block'")
            ws.send(json.dumps({
                "id": 602,
                "method": "DOM.setFileInputFiles",
                "params": {
                    "files": [CAMPAIGN['image_path']],
                    "nodeId": nid
                }
            }))
            ws.recv()
            run_js(ws, "document.querySelector('input[type=\"file\"]').dispatchEvent(new Event('change', {bubbles:true}))")
            print("Image Upload Triggered")
        else:
            print("Image Input Missing")
    except Exception as e:
        print(f"Image Error: {e}")

    time.sleep(2)
    
    # Click Next
    run_js(ws, "document.getElementById('saveBtn').disabled=false; document.getElementById('saveBtn').click()")
    print("Clicked Next (Details)")

    ws.close()

if __name__ == "__main__":
    main()
