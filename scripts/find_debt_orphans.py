
import json
import csv
import os

data_path = "data"

# Load unified campaigns
with open(os.path.join(data_path, "campaigns_unified.json"), 'r', encoding='utf-8') as f:
    unified = json.load(f)
    campaigns = unified.get("campaigns", [])

# Load coupling data
chuffed_ids_with_contacts = set()
with open(os.path.join(data_path, "coupling_vetting.csv"), 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['number'].strip() and 'x.com' not in row['number'] and '@' not in row['number']:
            chuffed_ids_with_contacts.add(row['chuffed_id'])

whydonate_titles_with_contacts = set()
with open(os.path.join(data_path, "whydonate_coupling_vetting.csv"), 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['number'].strip():
            whydonate_titles_with_contacts.add(row['whydonate_title'])

orphans_with_debt = []
for c in campaigns:
    is_orphan = False
    cid = c['id']
    if c['platform'] == 'chuffed':
        pure_id = cid.replace('chuffed_', '')
        if pure_id not in chuffed_ids_with_contacts:
            is_orphan = True
    elif c['platform'] == 'whydonate':
        if c['title'] not in whydonate_titles_with_contacts:
            is_orphan = True
    
    if is_orphan and c.get('raised_eur', 0) > 0:
        orphans_with_debt.append({
            'id': cid,
            'title': c['title'],
            'raised': c['raised_eur'],
            'platform': c['platform']
        })

print(f"Found {len(orphans_with_debt)} orphans with debt:")
for o in orphans_with_debt:
    print(f"- [{o['platform'].upper()}] {o['title']}: €{o['raised']}")
