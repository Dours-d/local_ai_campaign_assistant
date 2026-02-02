
import requests
import json
import websocket
import time
import os

CDP_URL = "http://localhost:9222/json"

CAMPAIGN = {
    "title": "Help Mohammed and his family rebuild their lives",
    "description": "Family in Gaza needs urgent support to rebuild their lives. Please donate generously.",
    "goal": 5000,
    "image_path": r"C:\Users\gaelf\Pictures\GAZA\Mohammed Ali\WhatsApp Image 2025-04-18 à 17.51.51_e46d624b.jpg"
}

def get_tab():
    try:
        r = requests.get(CDP_URL).json()
        for t in r:
            if 'whydonate.com' in t.get('url', '') and t['type'] == 'page':
                return t
        return None
    except:
        return None

def send_cdp(ws, method, params={}):
    msg = json.dumps({"id": int(time.time()*1000), "method": method, "params": params})
    ws.send(msg)
    res = ws.recv()
    return json.loads(res.replace('\n', '')) # Parse safety

def evaluate(ws, expression, await_promise=False):
    return send_cdp(ws, "Runtime.evaluate", {
        "expression": expression,
        "returnByValue": True,
        "awaitPromise": await_promise
    })

def main():
    print(f"Starting V2 automation...")
    
    # 1. Reset
    requests.put(f"{CDP_URL}/new?https://whydonate.com/fundraising/start")
    time.sleep(5)
    
    tab = get_tab()
    if not tab: return

    ws = websocket.create_connection(tab['webSocketDebuggerUrl'])
    
    # STEP 1
    print("Executing Step 1...")
    js_step1 = """
    (async function() {
        // 1. Click Category
        const cats = Array.from(document.querySelectorAll('.category-card, div[role="button"]'));
        const humanitarian = cats.find(el => el.innerText.includes("Humanitarian Aid"));
        if (humanitarian) {
             humanitarian.click();
        } else {
             return "CAT_NOT_FOUND";
        }
        
        await new Promise(r => setTimeout(r, 500));
        
        // 2. Type Address
        const address = document.getElementById('mat-input-0');
        if (address) {
            address.focus();
            address.value = "Netherlands";
            address.dispatchEvent(new Event('input', { bubbles: true }));
            address.blur();
        } else {
            return "ADDR_NOT_FOUND";
        }
        
        await new Promise(r => setTimeout(r, 1000));
        
        // 3. Click Next
        const btn = document.getElementById('saveStep1');
        if (btn) {
            btn.disabled = false;
            btn.click();
            return "SUCCESS";
        }
        return "BTN_NOT_FOUND";
    })()
    """
    res = evaluate(ws, js_step1, await_promise=True)
    print(f"Step 1: {res.get('result', {}).get('result', {}).get('value')}")
    
    time.sleep(3)
    
    # STEP 2 (Myself)
    print("Executing Step 2...")
    js_step2 = """
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
    res = evaluate(ws, js_step2, await_promise=True)
    print(f"Step 2: {res.get('result', {}).get('result', {}).get('value')}")
    
    time.sleep(3)
    
    # STEP 3 (Title)
    print("Executing Step 3 (Title)...")
    js_title = f"""
    (function() {{
        const title = document.querySelector('input[placeholder*="Title"]');
        if (title) {{
            title.focus();
            title.value = {json.dumps(CAMPAIGN['title'])};
            title.dispatchEvent(new Event('input', {{ bubbles: true }}));
            return "TITLE_SET";
        }}
        return "TITLE_NOT_FOUND";
    }})()
    """
    res = evaluate(ws, js_title)
    print(f"Title: {res.get('result', {}).get('result', {}).get('value')}")
    
    # UPLOAD
    print("Executing Step 3 (Image)...")
    doc = send_cdp(ws, "DOM.getDocument")
    if 'result' in doc and 'root' in doc['result']:
        root_id = doc['result']['root']['nodeId']
        node = send_cdp(ws, "DOM.querySelector", {"nodeId": root_id, "selector": "input[type='file']"})
        if 'nodeId' in node.get('result', {}):
             nid = node['result']['nodeId']
             evaluate(ws, "document.querySelector('input[type=\"file\"]').style.display='block'")
             send_cdp(ws, "DOM.setFileInputFiles", {"files": [CAMPAIGN['image_path']], "nodeId": nid})
             evaluate(ws, "document.querySelector('input[type=\"file\"]').dispatchEvent(new Event('change', { bubbles: true }))")
             print("Image upload triggered.")
        else:
             print("File input not found (DOM).")
    else:
        print("Could not get document root.")

    
    time.sleep(2)
    evaluate(ws, "document.getElementById('saveBtn').disabled = false; document.getElementById('saveBtn').click();")
    print("Clicked Next on Details.")
    
    ws.close()

if __name__ == "__main__":
    main()
