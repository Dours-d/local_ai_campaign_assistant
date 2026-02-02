
import requests
import json
import websocket
import time
import os

CDP_URL = "http://localhost:9222/json"

# Campaign Config - UPDATED FOR Mohammed and his family (128635)
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
    return json.loads(res)

def evaluate(ws, expression, await_promise=False):
    return send_cdp(ws, "Runtime.evaluate", {
        "expression": expression,
        "returnByValue": True,
        "awaitPromise": await_promise
    })

def main():
    print(f"Starting automation for: {CAMPAIGN['title']}")
    
    # 1. Reset to Start
    requests.put(f"{CDP_URL}/new?https://whydonate.com/fundraising/start")
    time.sleep(5)
    
    tab = get_tab()
    if not tab:
        print("No tab found.")
        return

    ws = websocket.create_connection(tab['webSocketDebuggerUrl'])
    
    # --- STEP 1: Category & Location ---
    print("Step 1: Category & Location")
    js_step1 = """
    (async function() {
        // Click Category
        const humanitarian = Array.from(document.querySelectorAll('*')).find(el => el.innerText === "Humanitarian Aid");
        if (humanitarian) humanitarian.click();
        
        // Type Address
        const address = document.getElementById('mat-input-0');
        if (address) {
            address.focus();
            address.value = "Netherlands";
            address.dispatchEvent(new Event('input', { bubbles: true }));
            address.blur();
        }
        
        // Wait and Click Next
        await new Promise(r => setTimeout(r, 1500));
        const btn = document.getElementById('saveStep1');
        if (btn) {
            btn.disabled = false;
            btn.click();
            return "SUCCESS";
        }
        return "FAIL";
    })()
    """
    res = evaluate(ws, js_step1, await_promise=True)
    print(f"Step 1 Result: {res.get('result', {}).get('result', {}).get('value')}")
    
    time.sleep(3)
    
    # --- STEP 2: Who is it for? (MYSELF) ---
    print("Step 2: Beneficiary Selector (Myself)")
    js_step2 = """
    (async function() {
        const els = Array.from(document.querySelectorAll('*'));
        // Find 'Myself' or 'Me'
        const myself = els.find(el => el.innerText === "Myself" || el.innerText === "Me" || el.innerText === "Mijzelf");
        
        if (myself) {
            // Traverse up to find the clickable card if needed
            const card = myself.closest('.fundraiser-type-card') || myself.closest('div[role="button"]');
            if (card) {
                card.click();
                return "CLICKED_MYSELF_CARD";
            }
            myself.click();
            return "CLICKED_MYSELF_TEXT";
        }
        return "NO_OPTION_FOUND";
    })()
    """
    res = evaluate(ws, js_step2, await_promise=True)
    print(f"Step 2 Result: {res.get('result', {}).get('result', {}).get('value')}")
    
    time.sleep(3)
    
    # --- STEP 3: Details (Title, Image) ---
    print("Step 3: Filling Details")
    
    # Set Title
    js_title = f"""
    (function() {{
        const title = document.getElementById('mat-input-1') || document.querySelector('input[placeholder*="Title"]');
        if (title) {{
            title.focus();
            title.value = {json.dumps(CAMPAIGN['title'])};
            title.dispatchEvent(new Event('input', {{ bubbles: true }}));
            title.blur();
            return "TITLE_SET";
        }}
        return "TITLE_NOT_FOUND";
    }})()
    """
    res = evaluate(ws, js_title)
    print(f"Title Set: {res.get('result', {}).get('result', {}).get('value')}")
    
    # Upload Image
    doc_res = send_cdp(ws, "DOM.getDocument")
    root_id = doc_res['result']['root']['nodeId']
    
    node_res = send_cdp(ws, "DOM.querySelector", {"nodeId": root_id, "selector": "input[type='file']"})
    
    if 'nodeId' in node_res['result']:
        node_id = node_res['result']['nodeId']
        print(f"Found file input node: {node_id}")
        
        # Unhide it if necessary
        evaluate(ws, "document.querySelector('input[type=\"file\"]').style.display='block'")
        
        send_cdp(ws, "DOM.setFileInputFiles", {
            "files": [CAMPAIGN['image_path']],
            "nodeId": node_id
        })
        print("File set.")
        
        # Trigger change to start upload
        evaluate(ws, "document.querySelector('input[type=\"file\"]').dispatchEvent(new Event('change', { bubbles: true }))")
    else:
        print("File input not found via DOM.")
    
    time.sleep(5)
    
    # Check Next Button on Details Page
    js_next_details = """
    (function() {
        const btn = document.getElementById('saveBtn');
        if (btn) {
            btn.disabled = false;
            btn.click();
            return "CLICKED_NEXT_DETAILS";
        }
        return "BTN_NOT_FOUND";
    })()
    """
    res = evaluate(ws, js_next_details)
    print(f"Details Next: {res.get('result', {}).get('result', {}).get('value')}")

    ws.close()

if __name__ == "__main__":
    main()
