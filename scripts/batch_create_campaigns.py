import requests
import json
import websocket
import time
import os
import sys

CDP_URL = "http://localhost:9222/json"
GAZA_PICTURES = r"C:\Users\gaelf\Pictures\GAZA"

MSG_ID = 1

def get_socket():
    global MSG_ID
    try:
        r = requests.get(CDP_URL).json()
        print(f"Debugger active tabs: {len(r)}")
        target_tab = None
        for t in r:
            if 'whydonate.com' in t.get('url', '') and t['type'] == 'page':
                target_tab = t
                break
        
        if not target_tab:
            print("No Whydonate tab found. Opening a new one...")
            requests.put(f"{CDP_URL}/new?https://whydonate.com/fundraising/start")
            time.sleep(5)
            r = requests.get(CDP_URL).json()
            for t in r:
                if 'whydonate.com' in t.get('url', '') and t['type'] == 'page':
                    target_tab = t
                    break
        
        if target_tab:
            print(f"Connecting to: {target_tab['url']}")
            ws = websocket.create_connection(target_tab['webSocketDebuggerUrl'])
            ws.settimeout(60)
            # Enable basic domains
            ws.send(json.dumps({"id": 10001, "method": "Page.enable"}))
            ws.send(json.dumps({"id": 10002, "method": "Runtime.enable"}))
            return ws
            
        return None
    except Exception as e:
        print(f"Socket error: {e}")
        return None

def run_js(ws, js, await_promise=True, timeout=60):
    global MSG_ID
    MSG_ID += 1
    this_id = MSG_ID
    msg = json.dumps({
        "id": this_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": js,
            "returnByValue": True,
            "awaitPromise": await_promise
        }
    })
    try:
        ws.send(msg)
        start_t = time.time()
        while time.time() - start_t < timeout:
            try:
                ws.settimeout(1)
                res_str = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            finally:
                ws.settimeout(60)
            
            debug_res = json.loads(res_str)
            if debug_res.get('id') == this_id:
                if 'exceptionDetails' in debug_res.get('result', {}):
                    print(f"JS Run Error [ID: {this_id}]: {debug_res['result']['exceptionDetails']}", flush=True)
                    return None
                val = debug_res.get('result', {}).get('result', {}).get('value')
                if val is None:
                    print(f"JS Result is None for ID {this_id}. Raw msg snippet: {res_str[:500]}", flush=True)
                return val
            
        print(f"JS Timeout [ID: {this_id}, {timeout}s]", flush=True)
        return None
    except Exception as e:
        print(f"JS Run Exception [ID: {this_id}]: {e}")
        return None

def find_local_image(title):
    print(f"Searching local images for campaign title parts...")
    words = title.replace(',', '').split()
    names = [w for w in words if w[0].isupper() and len(w) > 2]
    print(f"Looking for names: {names}")
    
    try:
        dirs = [d for d in os.listdir(GAZA_PICTURES) if os.path.isdir(os.path.join(GAZA_PICTURES, d))]
        for name in names:
            matches = [d for d in dirs if name.lower() in d.lower()]
            if matches:
                 # Check if match is a good one (not just a common word)
                 print(f"Found folder match: {matches[0]}")
                 target_dir = os.path.join(GAZA_PICTURES, matches[0])
                 images = [f for f in os.listdir(target_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                 # Filter out QR codes from local results too
                 valid_images = []
                 for img in images:
                     img_lower = img.lower()
                     if "qr" in img_lower or "code" in img_lower:
                         continue
                     
                     full_p = os.path.join(target_dir, img)
                     if os.path.getsize(full_p) < 25000: # 25KB minimum for local
                         continue
                     valid_images.append(full_p)

                 if valid_images:
                     p = os.path.abspath(valid_images[0])
                     print(f"Valid local image match: {p}")
                     return p
    except Exception as e:
        print(f"Image search error: {e}")
    return None

def download_image(url, campaign_id):
    if not url: return None
    # Skip if URL looks like a generic QR code
    if "qr" in url.lower() or "code" in url.lower():
        print(f"Skipping potential QR code URL: {url}")
        return None

    print(f"Downloading from {url}...")
    try:
        path = os.path.abspath(f"data/temp_image_{campaign_id}.jpg")
        r = requests.get(url, stream=True, timeout=10)
        if r.status_code == 200:
            content = r.content
            # Check size: QR codes or placeholders are often very small
            if len(content) < 10000: # 10KB
                print(f"Skipping downloaded image: too small ({len(content)} bytes), likely a QR or thumbnail.")
                return None
                
            with open(path, 'wb') as f:
                f.write(content)
            print(f"Saved to {path}")
            return path
    except Exception as e:
        print(f"Download error: {e}")
    return None

def check_connection(ws):
    """
    Performs a lightweight check to see if the connection and session are still alive.
    Returns: 'OK', 'LOGIN_REQUIRED', or 'DEAD'
    """
    try:
        # 1. Check if socket is open
        if not ws or not ws.connected:
            return "DEAD"
        
        # 2. Try a very simple JS call with a short timeout
        check_id = 99999
        msg = json.dumps({
            "id": check_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "window.location.href",
                "returnByValue": True
            }
        })
        ws.send(msg)
        
        start_t = time.time()
        res_url = None
        while time.time() - start_t < 3:
            try:
                ws.settimeout(0.5)
                res = json.loads(ws.recv())
                if res.get('id') == check_id:
                    res_url = res.get('result', {}).get('result', {}).get('value')
                    break
            except:
                continue
        
        if not res_url:
            return "DEAD"
        
        # 3. Check for login redirect
        if "/login" in res_url.lower() or "/account/login" in res_url.lower():
            return "LOGIN_REQUIRED"
            
        return "OK"
    except:
        return "DEAD"

def process_campaign(ws, campaign):
    global MSG_ID
    print(f"\n--- [START] {campaign['title']} ---", flush=True)
    
    # Navigating with retry
    for i in range(3):
        print(f"Navigation attempt {i+1}...", flush=True)
        global MSG_ID
        MSG_ID += 1
        nav_id = MSG_ID
        ws.send(json.dumps({"id": nav_id, "method": "Page.navigate", "params": {"url": "https://whydonate.com/fundraising/start"}}))
        print("Navigation command acknowledged.", flush=True)
        
        # Drain until navigation id or timeout
        start_n = time.time()
        while time.time() - start_n < 10:
            try:
                ws.settimeout(1)
                res = json.loads(ws.recv())
                if res.get('id') == nav_id: break
            except: continue
        
        # Poll for specific text or button
        check_js = """
        (async function() {
            if (window.location.href.includes('/login') || window.location.href.includes('/account/login')) return "LOGIN_REQUIRED";
            
            for (let i = 0; i < 20; i++) {
                const text = (document.body.innerText || "").toLowerCase();
                const hasButtons = document.querySelectorAll('button').length > 0;
                const hasChips = !!document.querySelector('mat-chip-option, mat-chip');
                const hasAddress = !!document.querySelector('input[placeholder*="address"]');
                
                const ok = text.includes('step 1') || 
                          text.includes('humanitarian') || 
                          text.includes('start fundraiser') ||
                          text.includes('whydonate') ||
                          hasButtons || 
                          hasAddress;
                          
                if (ok) return "OK";
                await new Promise(r => setTimeout(r, 250));
            }
            
            const text = (document.body.innerText || "").toLowerCase();
            return `DEBUG: final_text_len=${text.length}, buttons=${document.querySelectorAll('button').length > 0}`;
        })()
        """
        result = run_js(ws, check_js)
        if result == "LOGIN_REQUIRED":
            print("Session expired or redirected to login. Please ensure you are logged in.", flush=True)
            return "ERROR_LOGIN"
            
        if result == "OK":
            print("Page loaded (found text or button).", flush=True)
            
            # IMPROVED: Check if we are on the landing page and need to click "Start Fundraiser"
            is_landing = run_js(ws, """
                (function() {
                    const buttons = Array.from(document.querySelectorAll('button, a'));
                    const btn = buttons.find(b => (b.innerText || "").includes('Start Fundraiser'));
                    if (btn && !document.querySelector('input[placeholder*="address"]')) {
                        btn.click();
                        return true;
                    }
                    return false;
                })()
            """)
            if is_landing:
                print("Clicked 'Start Fundraiser' landing button. Waiting for form...", flush=True)
                time.sleep(8)
            break
        
        print(f"Page didn't load target elements (Attempt {i+1}). Result: {result}", flush=True)
        print(f"Current URL: {run_js(ws, 'window.location.href')}", flush=True)
        snippet = run_js(ws, "document.body.innerText.substring(0, 200)")
        print(f"Snippet: {snippet}", flush=True)
        time.sleep(5)
    else:
        print("Failed to reach start page after 3 attempts.", flush=True)
        return False
    
    # Image resolution
    final_image_path = find_local_image(campaign['title'])
    if not final_image_path:
        # Use chuffed_id or id if available
        cid = campaign.get('chuffed_id') or campaign.get('id') or "temp"
        final_image_path = download_image(campaign['image'], cid)
    
    if not final_image_path:
        print(f"ERROR: No valid image found (local or remote) for '{campaign['title']}'. Skipping to avoid QR/Bad image.")
        return False
    
    # STEP 1: Category & Location
    print("Step 1 execution...", flush=True)
    js1 = """
    (async function() {
        // Wait for form to be visible
        let attempts = 0;
        while (attempts < 20) {
            if (document.querySelector('input[placeholder*="address"]') || document.querySelector('mat-chip-option')) break;
            if (document.querySelector('mat-card, .fundraiser-type-card')) return "SKIPPED_ALREADY_ON_2";
            attempts++;
            await new Promise(r => setTimeout(r, 1000));
        }

        // Find category
        const findCat = () => {
            const spans = Array.from(document.querySelectorAll('span, mat-chip-option, mat-chip, .mat-mdc-chip-label'));
            const cat = spans.find(el => {
                const t = (el.innerText || "").toLowerCase();
                return t.includes('humanitarian') || t.includes('humanitair');
            });
            if (cat) return cat.closest('mat-chip-option') || cat.closest('mat-chip') || cat;
            return document.querySelector('mat-chip-option, mat-chip');
        };
        
        const chip = findCat();
        if (chip) {
            chip.scrollIntoView();
            if (chip.tagName === 'MAT-CHIP-OPTION') chip.setAttribute('aria-selected', 'true');
            chip.click();
            await new Promise(r => setTimeout(r, 1000));
        }
        
        const addr = document.querySelector('input[placeholder*="address"]');
        if (addr) {
            addr.focus();
            addr.value = "";
            const text = "Amsterdam, Netherlands";
            for (let char of text) {
                addr.value += char;
                addr.dispatchEvent(new Event('input', { bubbles: true }));
                await new Promise(r => setTimeout(r, 50));
            }
            // Wait for suggestions
            let suggestion = null;
            for (let i=0; i<15; i++) {
                suggestion = document.querySelector('.mat-mdc-option, .pac-item, mat-option, .autocomplete-suggestion');
                if (suggestion) break;
                await new Promise(r => setTimeout(r, 500));
            }
            if (suggestion) {
                suggestion.click();
                await new Promise(r => setTimeout(r, 1000));
            } else {
                // Fallback: Enter
                addr.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
                await new Promise(r => setTimeout(r, 500));
                addr.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
            }
        }
        
        await new Promise(r => setTimeout(r, 2000));
        
        const nextBtn = document.getElementById('saveStep1') || 
                        document.querySelector('button[id="saveStep1"]') ||
                        Array.from(document.querySelectorAll('button')).find(b => (b.innerText || "").includes('Next'));
        if (nextBtn) {
            nextBtn.disabled = false;
            nextBtn.click();
            return "SUCCESS";
        }
        return "NEXT_BUTTON_NOT_FOUND";
    })()
    """
    res1 = run_js(ws, js1, timeout=45)
    print(f"Step 1 Result: {res1}", flush=True)
    if not res1:
        print("Step 1 Failed. Stopping campaign process.")
        return False
    time.sleep(8)
    
    # STEP 2: Myself
    print("Step 2: Choosing target...", flush=True)
    js2 = """
    (async function() {
        if (document.querySelector('input[placeholder*="Title"]')) return "SKIPPED_ALREADY_ON_3";
        
        const targets = ["myself", "mijzelf", "yourself", "uzelf", "u zelf", "moi-même", "moi-meme"];
        let attempts = 0;
        while (attempts < 10) {
            const myself = Array.from(document.querySelectorAll('mat-card, .fundraiser-type-card, div[role="button"], span, p, h3, div')).find(el => {
                const t = (el.innerText || "").toLowerCase().trim();
                return targets.includes(t) || (el.children.length === 0 && targets.some(tgt => t.includes(tgt)));
            });

            if (myself) {
                const choice = myself.closest('mat-card, .fundraiser-type-card, div[role="button"], mat-chip-option') || myself;
                choice.click();
                await new Promise(r => setTimeout(r, 1500));
            } else {
                // Fallback: click first card-like thing
                const firstCard = document.querySelector('mat-card, .fundraiser-type-card, .selection-card');
                if (firstCard) {
                    firstCard.click();
                    await new Promise(r => setTimeout(r, 1000));
                }
            }
            
            const btn = document.getElementById('saveStep2') || 
                        Array.from(document.querySelectorAll('button')).find(b => {
                            const t = (b.innerText || "").toLowerCase();
                            return t.includes('next') || t.includes('volgende') || t.includes('suivant');
                        });
            if (btn) {
                btn.disabled = false;
                btn.click();
                // Wait to see if it moves
                await new Promise(r => setTimeout(r, 3000));
                if (document.querySelector('input[placeholder*="Title"]') || 
                    document.querySelector('input[formcontrolname="title"]') ||
                    document.querySelector('textarea')) {
                    return "SUCCESS";
                }
            }
            attempts++;
            await new Promise(r => setTimeout(r, 2000));
        }
        return "TARGET_BUTTON_NOT_FOUND_OR_STUCK";
    })()
    """
    res2 = run_js(ws, js2, timeout=60)
    print(f"Step 2 Result: {res2}", flush=True)
    if not res2 or "SUCCESS" not in res2 and "SKIPPED" not in res2:
        print("Step 2 Failed. Stopping campaign process.")
        return False
    time.sleep(5)
    
    # STEP 3: Details
    print("Step 3 execution...")
    
    raw_desc = (campaign.get('description') or "").strip()
    if len(raw_desc) < 200:
        raw_desc = raw_desc + "\n\nPlease support this fundraiser to help families in Gaza rebuild their lives. Every donation, no matter how small, makes a significant difference in providing essential aid and hope for a better future."

    # Primordial Publication Policy (Batching & Transparency Clause)
    internal_name = campaign.get('internal_name')
    # If no internal name is synced yet, fallback to title-based guess or "Pending"
    # But usually sync should have run.
    verif_line = f"Beneficiary ID: {internal_name}" if internal_name else "Beneficiary ID: Verifying..."

    policy_clause = (
        "\n\n---\n"
        "**Transparency & Disbursement Policy:**\n"
        f"**{verif_line}**\n"
        "Due to high international banking fees for high-risk regions, funds are disbursed in batches. "
        "Transfers are triggered once a minimum threshold of €100 is reached for a beneficiary. "
        "This ensures that your donation goes to the family, not to banking intermediaries. "
        "All historical donations are recorded and prioritized for disbursement."
    )
        
    desc = campaign['title'] + "\n\n" + raw_desc + policy_clause
    
    js3 = f"""
    (async function() {{
        try {{
            let attempts = 0;
            let titleInput = null;
            while (attempts < 40) {{
                titleInput = document.querySelector('input[placeholder*="Title"]') || 
                             document.querySelector('input[formcontrolname="title"]') ||
                             document.querySelector('input[id*="mat-input"]') ||
                             Array.from(document.querySelectorAll('input')).find(i => {{
                                 const p = (i.placeholder || "").toLowerCase();
                                 return p.includes("title") || p.includes("titel") || p.includes("titre");
                             }}) ||
                             Array.from(document.querySelectorAll('mat-label')).find(l => {{
                                 const lt = (l.innerText || "").toLowerCase();
                                 return lt.includes('title') || lt.includes('titel') || lt.includes('titre');
                             }})?.closest('mat-form-field, .mat-mdc-form-field')?.querySelector('input');
                if (titleInput) break;
                attempts++;
                await new Promise(r => setTimeout(r, 1000));
            }}
            
            if (!titleInput) {{
                const availableInputs = Array.from(document.querySelectorAll('input, textarea')).map(i => i.placeholder || i.getAttribute('formcontrolname') || i.id).join(', ');
                return "ERROR: TITLE_INPUT_NOT_FOUND. Available inputs: " + availableInputs;
            }}
            
            titleInput.focus();
            titleInput.value = {json.dumps(campaign['title'][:70])};
            titleInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            titleInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            
            const descInput = document.querySelector('textarea') || 
                              document.querySelector('div[contenteditable="true"]') ||
                              Array.from(document.querySelectorAll('textarea')).find(i => {{
                                  const p = (i.placeholder || "").toLowerCase();
                                  return p.includes("description") || p.includes("beschrijving");
                              }}) ||
                              Array.from(document.querySelectorAll('mat-label')).find(l => {{
                                  const lt = (l.innerText || "").toLowerCase();
                                  return lt.includes('description') || lt.includes('beschrijving');
                              }})?.closest('mat-form-field')?.querySelector('textarea');
                              
            if (descInput) {{
                descInput.focus();
                if (descInput.tagName === 'DIV') descInput.innerText = {json.dumps(desc)};
                else descInput.value = {json.dumps(desc)};
                descInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                descInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            
            const goalInput = document.querySelector('input[placeholder*="Target"]') || 
                              document.querySelector('input[placeholder*="amount"]') ||
                              document.querySelector('input[type="number"]') ||
                              document.querySelector('input[formcontrolname="amount"]') ||
                              Array.from(document.querySelectorAll('input')).find(i => {{
                                  const p = (i.placeholder || "").toLowerCase();
                                  return p.includes("goal") || p.includes("target") || p.includes("doel") || p.includes("bedrag");
                              }});
            if (goalInput) {{
                goalInput.focus();
                goalInput.value = "5000";
                goalInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                goalInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            
            return "SUCCESS: FILLED";
        }} catch(e) {{
            return "JS_EXCEPTION: " + e.message;
        }}
    }})()
    """
    res3 = run_js(ws, js3, timeout=60)
    print(f"Step 3 Details: {res3}")
    if not res3 or "SUCCESS" not in res3:
        print("Step 3 Failed. Stopping campaign process.")
        return False
    
    # Image Upload
    if final_image_path and os.path.exists(final_image_path):
        print(f"Uploading image: {final_image_path}")
        try:
            # We need a new requestId for each call
            MSG_ID += 1
            id1 = MSG_ID
            ws.send(json.dumps({"id": id1, "method": "DOM.getDocument"}))
            # Drain until we get result
            doc_res = None
            start_u = time.time()
            ws.settimeout(2)
            while time.time() - start_u < 10:
                try:
                    r = json.loads(ws.recv())
                    if r.get('id') == id1:
                        doc_res = r
                        break
                except: continue
            
            if doc_res:
                root = doc_res['result']['root']
                MSG_ID += 1
                id2 = MSG_ID
                ws.send(json.dumps({
                    "id": id2, 
                    "method": "DOM.querySelector", 
                    "params": {"nodeId": root['nodeId'], "selector": "input[type='file']"}
                }))
                # Drain
                node_res = None
                while time.time() - start_u < 15:
                    try:
                        r = json.loads(ws.recv())
                        if r.get('id') == id2:
                            node_res = r
                            break
                    except: continue
                
                if node_res and 'nodeId' in node_res.get('result', {}):
                    nid = node_res['result']['nodeId']
                    # Wrap in block to avoid redeclaration if run multiple times
                    run_js(ws, "{ const f = document.querySelector('input[type=\"file\"]'); if(f) f.style.display='block'; }")
                    MSG_ID += 1
                    id3 = MSG_ID
                    ws.send(json.dumps({
                        "id": id3,
                        "method": "DOM.setFileInputFiles",
                        "params": {"files": [final_image_path], "nodeId": nid}
                    }))
                    # Final drain for upload confirmation
                    while time.time() - start_u < 20:
                        try:
                            r = json.loads(ws.recv())
                            if r.get('id') == id3: break
                        except: continue
                    
                    ws.settimeout(60) # Restore
                    run_js(ws, "{ const f = document.querySelector('input[type=\"file\"]'); if(f) f.dispatchEvent(new Event('change', { bubbles: true })); }")
                    print("Image upload command sent. Waiting for upload process...", flush=True)
                    time.sleep(10) # Wait for backend processing of image
                else:
                    ws.settimeout(60)
                    print("File input not found.")
            else:
                ws.settimeout(60)
                print("Document root not found.")
        except Exception as e:
            print(f"Image Error: {e}")
    
    # Final click
    print("Step 4: Executing final click...", flush=True)
    js_final = """
    (async function() {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(r => setTimeout(r, 1000));
        
        // Handle new two-state switches (Public/Private, Publish/Draft)
        const toggles = Array.from(document.querySelectorAll('mat-slide-toggle, mat-button-toggle, mat-switch, .mdc-switch'));
        for (let t of toggles) {
            const label = (t.innerText || t.getAttribute('aria-label') || "").toLowerCase();
            const isChecked = t.classList.contains('mat-checked') || t.classList.contains('mat-button-toggle-checked') || (t.querySelector('input') && t.querySelector('input').checked);
            
            if ((label.includes('private') || label.includes('draft')) && isChecked) {
                t.click();
                await new Promise(r => setTimeout(r, 500));
            } else if ((label.includes('public') || label.includes('publish') || label.includes('online')) && !isChecked) {
                t.click();
                await new Promise(r => setTimeout(r, 500));
            }
        }

        // Find and click all checkboxes (Agreement, etc.)
        const checks = document.querySelectorAll('mat-checkbox:not(.mat-checkbox-checked), input[type="checkbox"]:not(:checked)');
        for (let ch of checks) {
            ch.click();
            await new Promise(r => setTimeout(r, 500));
        }

        const findAndClickBtn = () => {
             const btns = Array.from(document.querySelectorAll('button'));
             // Prioritize buttons in panels or dialogs
             const prioritized = btns.filter(b => b.closest('mat-dialog-container, .right-panel, .drawer, .modal'));
             const target = (prioritized.length > 0 ? prioritized : btns).find(b => {
                const t = (b.innerText || "").toLowerCase();
                return (t.includes('finish') || t.includes('publish') || t.includes('save') || t.includes('create') || t.includes('confirm')) && !b.disabled;
             });
             if (target) {
                 target.click();
                 return true;
             }
             return false;
        };

        let attempts = 0;
        while (attempts < 10) {
            if (findAndClickBtn()) return "SUCCESS_CLICKED";
            attempts++;
            await new Promise(r => setTimeout(r, 1500));
        }
        return "BUTTON_NOT_FOUND_OR_DISABLED";
    })()
    """
    res_final = run_js(ws, js_final)
    print(f"Final click result: {res_final}")
    
    # VERIFICATION: Check if URL changed/contains evidence of success
    final_url = None
    start_v = time.time()
    while time.time() - start_v < 20:
        final_url = run_js(ws, "window.location.href")
        if final_url and "fundraising/start" not in final_url:
            break
        time.sleep(2)
        
    print(f"Final URL after save: {final_url}")
    
    if final_url is None:
        print("COULD NOT RETRIEVE FINAL URL - Possible context destruction during navigation.")
        # We assume success if the context was destroyed by a navigation to a new page
        return True

    if "fundraising/start" in final_url:
        print("STILL ON START PAGE - Submission likely failed or was blocked by validation.", flush=True)
        # Extract visible errors and element states
        diag = run_js(ws, """
            (function() {
                const getButtons = () => Array.from(document.querySelectorAll('button')).map(b => ({
                    text: (b.innerText || "").trim(),
                    id: b.id,
                    disabled: b.disabled,
                    visible: b.offsetWidth > 0 && b.offsetHeight > 0,
                    classes: b.className
                }));
                const getToggles = () => Array.from(document.querySelectorAll('mat-slide-toggle, mat-button-toggle, mat-switch, .mdc-switch')).map(t => ({
                    label: (t.innerText || t.getAttribute('aria-label') || "").trim(),
                    checked: t.classList.contains('mat-checked') || t.classList.contains('mat-button-toggle-checked') || (t.querySelector('input') && t.querySelector('input').checked)
                }));
                
                return {
                    errors: Array.from(document.querySelectorAll('mat-error, .error-message, .alert-danger, .invalid-feedback, .error-text, .mat-mdc-snack-bar-label')).map(e => e.innerText.trim()).filter(t => t.length > 0),
                    buttons: getButtons(),
                    toggles: getToggles(),
                    total_text_len: document.body.innerText.length,
                    sample: document.body.innerText.substring(0, 3000)
                };
            })()
        """)
        print(f"VISIBLE ERRORS: {diag['errors']}", flush=True)
        print(f"BUTTONS FOUND: {json.dumps(diag['buttons'], indent=2)}", flush=True)
        print(f"TOGGLES FOUND: {json.dumps(diag['toggles'], indent=2)}", flush=True)
        
        # Check for specific "Title exists" or similar in whole page text
        page_text = (diag['sample'] or "").lower()
        if "already exists" in page_text:
            print("DETECTED: Campaign title already exists in your account.", flush=True)
        if "too long" in page_text:
            print("DETECTED: One of the fields is too long.", flush=True)
        if "required" in page_text:
            print("DETECTED: A mandatory field is missing.", flush=True)
            
        print(f"Page Snippet (Long): {diag['sample'][:2000]}")
            
        return False

    # Cleanup temp image
    if final_image_path and "temp_image" in final_image_path:
        try: os.remove(final_image_path)
        except: pass
    
    return True

def normalize_title(t):
    import re
    # Remove special characters, handle non-breaking spaces, lowercase everything
    t = t.replace('\u00a0', ' ').lower()
    t = re.sub(r'[^a-z0-9 ]', '', t)
    return " ".join(t.split())

def check_for_double(title, existing_campaigns):
    target = normalize_title(title)
    for existing in existing_campaigns:
        ext = normalize_title(existing.get('title', ''))
        # Check for high similarity or containment
        if target == ext or target in ext or ext in target:
            return True
    return False

def main():
    BATCH_JSON = os.path.join(os.getcwd(), 'data', 'whydonate_batch_create.json')
    MAX_BATCH = 5
    existing_file = "data/whydonate_all_campaigns.json"
    
    if not os.path.exists(BATCH_JSON):
        print("Batch file missing.")
        return

    # Load existing to avoid doubles
    existing_campaigns = []
    if os.path.exists(existing_file):
        with open(existing_file, 'r', encoding='utf-8') as f:
            existing_campaigns = json.load(f)
    print(f"Loaded {len(existing_campaigns)} existing campaigns to check for doubles.")

    with open(BATCH_JSON, 'r', encoding='utf-8') as f:
        campaigns = json.load(f)

    ws = get_socket()
    if not ws:
        print("Please open Chrome with remote debugging on port 9222 and navigate to whydonate.com")
        return

    count = 0
    # Process all remaining pending campaigns
    total_pending = len([c for c in campaigns if c.get('status') == 'pending_migration'])
    print(f"Starting full creation for {total_pending} remaining campaigns...", flush=True)
    
    for c in campaigns: # Changed 'campaign' to 'c' to match the instruction's retry block
        if c.get('status') == 'pending_migration':
            # Check for doubles
            if check_for_double(c['title'], existing_campaigns):
                print(f"Found double for: {c['title']}. Marking as already_exists.")
                c['status'] = 'already_exists'
                with open(BATCH_JSON, 'w', encoding='utf-8') as f:
                    json.dump(campaigns, f, indent=2)
                continue
            if count >= MAX_BATCH: break
        
            # Attempt with retry and refresh
            success = False
            for attempt in range(3):
                res = False # Initialize
                if attempt > 0:
                    print(f"RETRY {attempt} for '{c['title']}' - Refreshing page...", flush=True)
                    ws.send(json.dumps({"id": 8888, "method": "Page.reload"}))
                    time.sleep(10)
                
                # PRE-FLIGHT CHECK
                conn_status = check_connection(ws)
                if conn_status == "DEAD":
                    print("!!! CONNECTION DEAD !!!", flush=True)
                    break 
                elif conn_status == "LOGIN_REQUIRED":
                    print("!!! LOGIN REQUIRED !!!", flush=True)
                    break
                
                res = process_campaign(ws, c)
                if res is True:
                    success = True
                    break
                elif res == "ERROR_LOGIN":
                    break
                
                print(f"Attempt {attempt+1} failed.", flush=True)
            
            if success:
                c['status'] = 'created_initial'
                c['processed_at'] = datetime.now().isoformat()
                count += 1
                with open(BATCH_JSON, 'w', encoding='utf-8') as f:
                    json.dump(campaigns, f, indent=2)
                print(f"SUCCESS: Campaign created. Finished {count}/{total_pending}. Waiting 15s...")
                time.sleep(15)
            elif res == "ERROR_LOGIN": # This condition is already handled inside the loop, but keeping it for consistency with the instruction's provided block.
                print("FAILURE: Login required. Stopping.")
                break
                with open(batch_file, 'w', encoding='utf-8') as f:
                    json.dump(campaigns, f, indent=2)
                # Continue to next to see if it's a general issue or specific to this record
                time.sleep(5)
                continue 

    ws.close()

if __name__ == "__main__":
    main()
