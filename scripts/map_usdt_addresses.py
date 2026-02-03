import os
import re

addresses_file = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\unique_atomic_usdt_addresses.txt'
exports_dir = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\exports'
output_file = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\usdt_address_mapping.csv'

with open(addresses_file, 'r', encoding='utf-8') as f:
    addresses = [line.strip() for line in f if line.strip()]

mapping = []
for addr in addresses:
    print(f"Searching for {addr}...")
    for filename in os.listdir(exports_dir):
        if filename.endswith('.txt'):
            filepath = os.path.join(exports_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if addr in content:
                        mapping.append((addr, filename))
                        print(f"Found {addr} in {filename}")
            except Exception as e:
                print(f"Error reading {filename}: {e}")

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("USDTAddress,ExportFile\n")
    for addr, export in mapping:
        f.write(f"{addr},{export}\n")

print(f"Finished. Found {len(mapping)} matches.")
