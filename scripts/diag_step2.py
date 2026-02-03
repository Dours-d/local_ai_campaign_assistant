
import json
import websocket
import requests
import time

CDP_URL = "http://localhost:9222/json"

def run_js(ws, js):
    msg = json.dumps({
        "id": 200,
        "method": "Runtime.evaluate",
        "params": {"expression": js, "returnByValue": True, "awaitPromise": True}
    })
    ws.send(msg)
    while True:
        try:
            res = json.loads(ws.recv())
            if res.get('id') == 200:
                if 'exceptionDetails' in res.get('result', {}):
                    print(f"JS EXCEPTION: {res['result']['exceptionDetails']}")
                return res.get('result', {}).get('result', {}).get('value')
        except: continue

def main():
    r = requests.get(CDP_URL).json()
    target = next((t for t in r if 'whydonate.com/fundraising/start' in t.get('url', '') and t['type'] == 'page'), None)
    if not target:
        print("Start page not found.")
        return

    ws = websocket.create_connection(target['webSocketDebuggerUrl'])
    
    js1 = """
    (async function() {
        const debug = {};
        const span = Array.from(document.querySelectorAll('span')).find(el => (el.innerText || '').includes('Humanitarian'));
        const chip = span ? span.closest('mat-chip-option') : null;
        if (chip) {
            debug.chipBefore = chip.className;
            chip.scrollIntoView();
            chip.click();
            await new Promise(r => setTimeout(r, 1000));
            debug.chipAfter = chip.className;
        }
        
        const addr = document.querySelector('input[placeholder*="address"]');
        if (addr) {
            addr.focus();
            addr.value = "";
            for (let char of "Amsterdam, Netherlands") {
                addr.value += char;
                addr.dispatchEvent(new Event('input', { bubbles: true }));
            }
            await new Promise(r => setTimeout(r, 2500));
            const sugg = document.querySelector('.mat-option, .mat-mdc-option, .pac-item, .autocomplete-suggestion');
            if (sugg) {
                sugg.click();
                await new Promise(r => setTimeout(r, 1000));
            }
            debug.addressVal = addr.value;
        }
        
        const btn = document.getElementById('saveStep1') || 
                    Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Next'));
        if (btn) {
            debug.btnHTML = btn.outerHTML;
            debug.btnDisabled = btn.disabled;
            btn.disabled = false;
            btn.click();
            return { res: "CLICKED_NEXT", debug };
        }
        return { res: "NEXT_NOT_FOUND", debug };
    })()
    """
    print(run_js(ws, js1))
    
    # Wait for Step 2
    for i in range(10):
        url = run_js(ws, "window.location.href")
        text = run_js(ws, "document.body.innerText")
        has_myself = "Myself" in text or "Mijzelf" in text
        has_btn2 = run_js(ws, "!!document.getElementById('saveStep2')")
        
        if has_myself or has_btn2:
            print(f"Step 2 detected! (Myself: {has_myself}, Button2: {has_btn2})")
            break
        print(f"Waiting for Step 2... (URL: {url})")
        # Dump some buttons to see what's there
        btns = run_js(ws, "Array.from(document.querySelectorAll('button')).map(b => ({id: b.id, text: b.innerText}))")
        print(f"Buttons: {btns}")
        time.sleep(2)
        
    print("Performing Step 2...")
    js2 = """
    (async function() {
        const els = Array.from(document.querySelectorAll('*'));
        const myself = els.find(el => {
            const t = (el.innerText || "").toLowerCase();
            return t === "myself" || t === "mijzelf" || (el.children.length === 0 && (t.includes("myself") || t.includes("mijzelf")));
        });
        
        if (myself) {
            console.log("Found myself, clicking");
            const choice = myself.closest('mat-card, .fundraiser-type-card, div[role="button"], mat-chip-option');
            if (choice) choice.click();
            else myself.click();
            await new Promise(r => setTimeout(r, 1000));
        } else {
            // Fallback: click the first choice card
            const firstCard = document.querySelector('mat-card, .fundraiser-type-card');
            if (firstCard) firstCard.click();
        }
        
        const btn = document.getElementById('saveStep2') || 
                    Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Next'));
        if (btn) {
            btn.disabled = false;
            btn.click();
            return "STEP2_DONE";
        }
        return "STEP2_NEXT_NOT_FOUND";
    })()
    """
    print(run_js(ws, js2))
    
    # Wait for Step 3
    for i in range(10):
        url = run_js(ws, "window.location.href")
        text = run_js(ws, "document.body.innerText")
        if "Title" in text or "Description" in text or "Target" in text:
            print("Step 3 detected!")
            break
        print(f"Waiting for Step 3... (URL: {url})")
        time.sleep(2)
        
    print("--- URL AFTER STEP 2 ---")
    print(run_js(ws, "window.location.href"))
    
    # Check for Step 3
    print("--- FORM ELEMENTS IN STEP 3 ---", flush=True)
    js_diag = """
    (function() {
        return Array.from(document.querySelectorAll('input, textarea, mat-select, button, div[contenteditable]')).map(el => ({
            tag: el.tagName,
            placeholder: el.placeholder || el.getAttribute('placeholder'),
            id: el.id,
            text: el.innerText.trim().substring(0, 50),
            type: el.type,
            name: el.name,
            classes: el.className
        }));
    })()
    """
    print(run_js(ws, js_diag), flush=True)
    
    # Dump body HTML snippet
    print("--- BODY HTML SNIPPET ---", flush=True)
    print(run_js(ws, "document.body.innerHTML.substring(0, 1000)"), flush=True)
    
    time.sleep(5)
    print("--- URL AFTER STEP 1 ---")
    print(run_js(ws, "window.location.href"))
    
    print("--- VISIBLE ERRORS ---")
    print(run_js(ws, "Array.from(document.querySelectorAll('mat-error')).map(e => e.innerText)"))
    
    print("--- PAGE TEXT SNIPPET ---")
    print(run_js(ws, "document.body.innerText.substring(0, 1000)"))
    
    ws.close()

if __name__ == "__main__":
    main()
