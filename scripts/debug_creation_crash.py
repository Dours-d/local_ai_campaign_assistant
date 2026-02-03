import json
import sys
import os
sys.path.append(os.getcwd())
from scripts.batch_create_campaigns import get_socket, process_campaign, check_connection
import time

def debug_one():
    with open('data/whydonate_batch_create.json', 'r', encoding='utf-8') as f:
        campaigns = json.load(f)
    
    # Pick the first pending one
    c = next((item for item in campaigns if item.get('status') == 'pending_migration'), None)
    if not c:
        print("No pending campaigns found.")
        return

    print(f"DEBUGGING SINGLE CAMPAIGN: {c['title']}")
    ws = get_socket()
    
    try:
        conn = check_connection(ws)
        print(f"Connection status: {conn}")
        if conn != "OK":
            print("Session not ready. Please check browser.")
            return

        res = process_campaign(ws, c)
        print(f"FINAL RESULT: {res}")
    except Exception as e:
        import traceback
        print("!!! CRASH DETECTED !!!")
        traceback.print_exc()
    finally:
        ws.close()

if __name__ == "__main__":
    debug_one()
