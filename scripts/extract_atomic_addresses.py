import csv
import json
import os
import traceback

atomic_log_path = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\atomic_wallet_log\history-atomicwallet-02.02.2026.csv'
output_path = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\unique_atomic_usdt_addresses.txt'

addresses = set()
try:
    with open(atomic_log_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('OUTCURRENCY') == 'TRX-USDT':
                addr = row.get('ADDRESSTO')
                if addr and addr != '-':
                    addresses.add(addr)
except Exception as e:
    print(f"Error reading CSV: {e}")
    traceback.print_exc()

if addresses:
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for addr in sorted(list(addresses)):
                f.write(addr + '\n')
        print(f"Extracted {len(addresses)} unique USDT addresses to {output_path}.")
    except Exception as e:
        print(f"Error writing output: {e}")
        traceback.print_exc()
else:
    print("No addresses found or error occurred.")
