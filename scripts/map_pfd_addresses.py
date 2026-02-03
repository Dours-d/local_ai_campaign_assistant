import csv
import os
import glob

analysis_path = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\atomic_fund_analysis.csv'
exports_dir = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\exports'
output_mapping = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\pfd_address_mapping.csv'

# Get addresses of uncoupled transactions
pfd_addresses = set()
with open(analysis_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['coupled'] == 'False':
            pfd_addresses.add(row['address'])

print(f"Searching for {len(pfd_addresses)} PFD addresses in exports...")

mapping = []
html_files = glob.glob(os.path.join(exports_dir, "*.html"))
json_files = glob.glob(os.path.join(exports_dir, "*.json"))
txt_files = glob.glob(os.path.join(exports_dir, "*.txt"))

all_files = html_files + json_files + txt_files

for addr in pfd_addresses:
    found_in = []
    for file_path in all_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if addr in content:
                    found_in.append(os.path.basename(file_path))
        except Exception as e:
            pass
    
    mapping.append({
        'address': addr,
        'files': ", ".join(found_in) if found_in else "NOT FOUND"
    })

with open(output_mapping, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['address', 'files'])
    writer.writeheader()
    writer.writerows(mapping)

print(f"Mapping saved to {output_mapping}")
