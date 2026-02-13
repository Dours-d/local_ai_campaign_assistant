
import re
import os
import json

def update_public_link():
    log_path = 'data/tunnel.log'
    target_file = 'docs/public_brain.html'
    
    if not os.path.exists(log_path):
        print("Log file not found.")
        return

    url = None
    # Read entire log file (it was cleared recently)
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        # Look for standard URL
        match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', content)
        if match:
            url = match.group(0)
        else:
            # Look for escaped JSON URL
            match = re.search(r'https:\\/\\/[a-z0-9-]+\.trycloudflare\.com', content)
            if match:
                url = match.group(0).replace('\\/', '/')
    
    if url:
        print(f"Found Tunnel URL: {url}")
        
        with open(target_file, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Replace the const targetUrl value
        new_html = re.sub(r'const targetUrl = "[^"]+";', f'const targetUrl = "{url}";', html)
        
        if html != new_html:
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(new_html)
            print(f"Updated {target_file}")
        else:
            print("File already up to date.")
            
    else:
        print("URL not found in log.")

if __name__ == "__main__":
    update_public_link()
