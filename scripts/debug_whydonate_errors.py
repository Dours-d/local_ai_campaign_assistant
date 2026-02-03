
import json
import websocket
import requests
import time

CDP_URL = "http://localhost:9222/json"

def run_js(ws, js):
    msg = json.dumps({
        "id": 100,
        "method": "Runtime.evaluate",
        "params": {"expression": js, "returnByValue": True, "awaitPromise": True}
    })
    ws.send(msg)
    while True:
        try:
            res = json.loads(ws.recv())
            if res.get('id') == 100:
                return res.get('result', {}).get('result', {}).get('value')
        except: continue

def main():
    r = requests.get(CDP_URL).json()
    target = next((t for t in r if 'whydonate.com/fundraising/start' in t.get('url', '') and t['type'] == 'page'), None)
    if not target:
        print("Start page not found in tabs.")
        return

    ws = websocket.create_connection(target['webSocketDebuggerUrl'])
    
    print("Extracting errors from the current page...")
    errors = run_js(ws, """
        Array.from(document.querySelectorAll('mat-error, .error-message, .alert-danger, .invalid-feedback'))
            .map(e => e.innerText.trim())
            .filter(t => t.length > 0)
    """)
    print(f"VISIBLE ERRORS: {errors}")
    
    page_text = run_js(ws, "document.body.innerText")
    if "already exists" in page_text.lower():
        print("Detected 'Already Exists' error in page text.")
    
    # Identify Step
    step = "UNKNOWN"
    if "Category" in page_text or "Categorie" in page_text: step = "STEP 1 (Category)"
    if "Target" in page_text or "Myself" in page_text or "Mijzelf" in page_text: step = "STEP 2 (Target)"
    if "Title" in page_text or "Description" in page_text: step = "STEP 3 (Details)"
    print(f"Current Step: {step}")
    
    # List all buttons
    btns = run_js(ws, "Array.from(document.querySelectorAll('button')).map(b => b.innerText.trim())")
    print(f"Buttons on page: {btns}")
    
    ha_tags = run_js(ws, """
        Array.from(document.querySelectorAll('mat-chip-option, button, div, span'))
            .filter(el => el.innerText && el.innerText.length < 100)
            .map(el => ({ tag: el.tagName, text: el.innerText.trim() }))
    """)
    print(f"Elements: {ha_tags}")
    
    mat_tags = run_js(ws, "Array.from(document.querySelectorAll('*')).filter(el => el.tagName.startsWith('MAT-')).map(el => el.tagName)")
    print(f"Material Tags: {set(mat_tags)}")

    # Check for empty title or description
    inputs = run_js(ws, """
        ({
            title: document.querySelector('input[placeholder*="Title"]')?.value || "NOT_FOUND",
            desc: document.querySelector('textarea')?.value || "NOT_FOUND",
            image: !!document.querySelector('img[src*="blob"], img[src*="http"]')
        })
    """)
    print(f"Form State: {inputs}")
    
    ws.close()

if __name__ == "__main__":
    main()
