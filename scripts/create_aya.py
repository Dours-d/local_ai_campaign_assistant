
import requests
import json
import websocket
import time
import os

CDP_URL = "http://localhost:9222/json"

# Campaign Config for Aya and her family (130620)
CAMPAIGN = {
    "title": "Help Aya and her family survive the bombing",
    "description": "Please help Aya and her family survive these difficult times in Gaza. Your support can save lives.",
    "goal": 5000,
    "image_path": r"C:\Users\gaelf\Pictures\GAZA\Aya Pop\WhatsApp Image 2025-05-05 à 15.24.46_18db6520.jpg"
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

def run_js(ws, js, await_promise=True):
    msg = json.dumps({
        "id": int(time.time() * 1000),
        "method": "Runtime.evaluate",
        "params": {
            "expression": js,
            "returnByValue": True,
            "awaitPromise": await_promise
        }
    })
    ws.send(msg)
    while True:
        res = json.loads(ws.recv())
        if res.get('id') == json.loads(msg)['id']:
            if 'exceptionDetails' in res.get('result', {}):
                print(f"JS Error: {res['result']['exceptionDetails']}")
                return None
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
        
    # Reset to start
    run_js(ws, "window.location.href = 'https://whydonate.com/fundraising/start';", await_promise=False)
    print("Navigating to start...")
    time.sleep(5)

    # STEP 1: Category & Location
    print("Step 1 (Category & Location)...")
    js1 = """
    (async function() {
        const h = Array.from(document.querySelectorAll('*')).find(el => el.innerText === "Humanitarian Aid");
        if (h) h.click();
        
        await new Promise(r => setTimeout(r, 500));
        
        // Search for address input by type/placeholder
        const addr = document.querySelector('input[placeholder*="address"]' ) || document.querySelector('input[type="text"]'); 
        
        if (addr) {
            addr.value = "Netherlands";
            addr.dispatchEvent(new Event('input', {bubbles:true}));
        } else {
             return "ADDR_INPUT_MISSING";
        }
        
        await new Promise(r => setTimeout(r, 1000));
        
        const btn = document.getElementById('saveStep1') || document.querySelector('button[id="saveStep1"]');
        if (btn) {
            btn.disabled = false;
            btn.click();
            return "NEXT_CLICKED";
        }
        return "BTN_MISSING";
    })()
    """
    res1 = run_js(ws, js1)
    print(f"Result 1: {res1}")
    time.sleep(4)

    # STEP 2: Myself (Handling potential skip or appearance)
    print("Step 2 (Myself)...")
    js2 = """
    (async function() {
        const els = Array.from(document.querySelectorAll('.fundraiser-type-card, div[role="button"]'));
        const myself = els.find(el => el.innerText.includes("Myself") || el.innerText.includes("Me") || el.innerText.includes("Mijzelf"));
        if (myself) {
            myself.click();
            return "CLICKED_MYSELF";
        }
        if (document.querySelector('input[placeholder="Fundraiser Title"]')) {
            return "SKIPPED_STEP_2";
        }
        return "MYSELF_NOT_FOUND";
    })()
    """
    res2 = run_js(ws, js2)
    print(f"Result 2: {res2}")
    time.sleep(4)

    # STEP 3: Details
    print("Step 3 (Details)...")
    js3_title = f"""
    (function() {{
        const t = document.querySelector('input[placeholder="Fundraiser Title"]');
        if (t) {{
            t.value = {json.dumps(CAMPAIGN['title'])};
            t.dispatchEvent(new Event('input', {{bubbles:true}}));
            return "TITLE_SET";
        }}
        return "TITLE_NOT_FOUND";
    }})()
    """
    print(f"Title: {run_js(ws, js3_title)}")

    js3_desc = f"""
    (function() {{
        const d = document.querySelector('textarea');
        if (d) {{
            d.value = {json.dumps(CAMPAIGN['description'])};
            d.dispatchEvent(new Event('input', {{bubbles:true}}));
            return "DESC_SET";
        }}
        return "DESC_NOT_FOUND";
    }})()
    """
    print(f"Desc: {run_js(ws, js3_desc)}")

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
            run_js(ws, "document.querySelector('input[type=\"file\"]').style.display='block';")
            ws.send(json.dumps({
                "id": 602,
                "method": "DOM.setFileInputFiles",
                "params": {
                    "files": [CAMPAIGN['image_path']],
                    "nodeId": nid
                }
            }))
            ws.recv()
            run_js(ws, "document.querySelector('input[type=\"file\"]').dispatchEvent(new Event('change', {bubbles:true}));")
            print("Image Upload Triggered")
        else:
            print("Image Input Missing")
    except Exception as e:
        print(f"Image Error: {e}")

    time.sleep(3)
    
    # Click Next
    run_js(ws, "document.getElementById('saveBtn').disabled=false; document.getElementById('saveBtn').click()")
    print("Clicked Next (Details)")

    ws.close()

if __name__ == "__main__":
    main()
