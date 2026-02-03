import csv
import os
import subprocess

analysis_path = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\atomic_fund_analysis.csv'
live_extract_path = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\whatsapp_live_extract.txt'
output_pfd_matching = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\pfd_whatsapp_matches.csv'

# Get uncoupled addresses
uncoupled = []
with open(analysis_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['coupled'] == 'False':
            uncoupled.append(row)

print(f"Checking {len(uncoupled)} uncoupled transactions...")

results = []
for tx in uncoupled:
    addr = tx['address']
    # Use rg to find the address in live extract
    try:
        # Get 2 lines before and after for context
        process = subprocess.Popen(['rg', '-A', '2', '-B', '2', addr, live_extract_path],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        
        if stdout:
            tx['whatsapp_context'] = stdout.strip()
            results.append(tx)
            print(f"MATCH FOUND for {addr}!")
        else:
            # tx['whatsapp_context'] = "NOT FOUND"
            pass
    except Exception as e:
        print(f"Error searching for {addr}: {e}")

with open(output_pfd_matching, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['date', 'type', 'amount', 'address', 'coupled', 'coupling_info', 'txid', 'whatsapp_context'])
    writer.writeheader()
    writer.writerows(results)

print(f"Matches saved to {output_pfd_matching}")
print(f"Total matches found: {len(results)}")
