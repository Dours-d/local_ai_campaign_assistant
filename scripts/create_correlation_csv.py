
import json
import csv
import os

data_path = "data"
unified_path = os.path.join(data_path, "campaigns_unified.json")
chuffed_map_path = os.path.join(data_path, "coupling_vetting.csv")
whydonate_map_path = os.path.join(data_path, "whydonate_coupling_vetting.csv")
output_path = os.path.join(data_path, "manual_correlation_backlog.csv")

# 1. Load Unified Campaigns
with open(unified_path, 'r', encoding='utf-8') as f:
    campaigns = json.load(f).get("campaigns", [])

# 2. Load Existing Mappings to find gaps
chuffed_mapped = set()
if os.path.exists(chuffed_map_path):
    with open(chuffed_map_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            chuffed_mapped.add(row.get('chuffed_id', ''))

whydonate_mapped = set()
if os.path.exists(whydonate_map_path):
    with open(whydonate_map_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            whydonate_mapped.add(row.get('whydonate_title', ''))

# 3. Create cross-platform beneficiary index (to suggest numbers)
ben_to_number = {}
if os.path.exists(chuffed_map_path):
    with open(chuffed_map_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            num = row.get('number', '').strip()
            if num and 'x.com' not in num and '@' not in num:
                ben_to_number[row.get('beneficiary', '')] = num

if os.path.exists(whydonate_map_path):
    with open(whydonate_map_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            num = row.get('number', '').strip()
            if num and 'x.com' not in num and '@' not in num:
                ben_to_number[row.get('beneficiary', '')] = num

# 4. Identify unmatched campaigns and correlate
backlog = []
for c in campaigns:
    cid = c['id']
    title = c['title']
    ben = c['privacy']['first_name']
    platform = c['platform']
    raised = c.get('raised_eur', 0)
    
    is_mapped = False
    if platform == 'chuffed':
        pure_id = cid.replace('chuffed_', '')
        if pure_id in chuffed_mapped:
            is_mapped = True
    else: # whydonate
        if title in whydonate_mapped:
            is_mapped = True
            
    if not is_mapped:
        suggested_num = ben_to_number.get(ben, "")
        status = "GAP (Known beneficiary)" if suggested_num else "MISSING (Unknown person)"
        
        backlog.append({
            'platform': platform,
            'campaign_id': cid,
            'beneficiary': ben,
            'title': title,
            'raised_eur': raised,
            'suggested_number': suggested_num,
            'correlation_status': status,
            'manual_number': "", # Column for user to fill
            'manual_note': ""    # Column for user to fill
        })

# 5. Sort by Raised (Debt first) then Status
backlog.sort(key=lambda x: (x['correlation_status'], -x['raised_eur']))

# 6. Write CSV
fieldnames = ['platform', 'beneficiary', 'suggested_number', 'manual_number', 'raised_eur', 'correlation_status', 'title', 'campaign_id', 'manual_note']
with open(output_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in backlog:
        writer.writerow(row)

print(f"Created correlation catalog: {output_path}")
print(f"Total campaigns requiring correlation: {len(backlog)}")
print(f"High-priority gaps (debt): {len([b for b in backlog if b['raised_eur'] > 0])}")
