import re
import os

live_extract_path = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\whatsapp_live_extract.txt'
output_path = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\extracted_pfd_contacts.csv'

target_names = ["Mohamad Al-Baz", "Yahya Al-Baz", "Sister Raghda", "Ahed", "Abdul Rahman", "Mahmoud"]

# TRC20 Address Regex: Starts with T, 34 chars, alphanumeric
usdt_pattern = re.compile(r'\bT[a-zA-Z0-9]{33}\b')

# Line format: [Timestamp] Name: Message
message_re = re.compile(r'\[.*?\] (.*?): (.*)')

results = []
current_sender = None

with open(live_extract_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        match = message_re.match(line)
        if match:
            sender = match.group(1)
            text = match.group(2)
            
            # Check if sender is one of our targets
            is_target = any(target.lower() in sender.lower() for target in target_names)
            
            if is_target:
                addresses = usdt_pattern.findall(text)
                for addr in addresses:
                    results.append({
                        'name': sender,
                        'address': addr,
                        'message': text.strip()
                    })

# deduplicate
unique_results = []
seen = set()
for r in results:
    key = (r['name'], r['address'])
    if key not in seen:
        unique_results.append(r)
        seen.add(key)

import csv
with open(output_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['name', 'address', 'message'])
    writer.writeheader()
    writer.writerows(unique_results)

print(f"Extracted {len(unique_results)} addresses from {len(results)} mentions.")
print(f"Saved to {output_path}")
