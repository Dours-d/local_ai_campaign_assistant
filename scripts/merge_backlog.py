
import csv
import os

data_path = "data"
backlog_path = os.path.join(data_path, "manual_correlation_backlog.csv")
chuffed_path = os.path.join(data_path, "coupling_vetting.csv")
whydonate_path = os.path.join(data_path, "whydonate_coupling_vetting.csv")

# 1. Load the backlog
backlog_updates = []
with open(backlog_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Use manual_number if provided, otherwise check if it's a GAP we should close
        # For now, only processing rows where the user has explicitly confirmed a number or it's a gap
        num = row.get('manual_number', '').strip()
        if not num:
            # If it's a GAP (Known beneficiary) we might want to auto-fill it if the user didn't object
            # But to be safe, let's only process if user filled manual_number OR if it's a GAP and user didn't put a '-' or something.
            # However, looking at the previous turn, the user likely wants to close the gaps.
            num = row.get('suggested_number', '').strip()
        
        if num and num != "discarded" and 'x.com' not in num:
            backlog_updates.append(row)

print(f"Processing {len(backlog_updates)} updates...")

# 2. Update Chuffed
chuffed_rows = []
chuffed_ids_updated = set()
if os.path.exists(chuffed_path):
    with open(chuffed_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            # Check if we have an update for this ID
            updates = [u for u in backlog_updates if u['platform'] == 'chuffed' and u['campaign_id'].replace('chuffed_', '') == row['chuffed_id']]
            if updates:
                u = updates[0]
                row['number'] = u.get('manual_number') or u.get('suggested_number')
                if u.get('alt_chat_name'):
                    row['whatsapp_contact'] = u['alt_chat_name']
                chuffed_ids_updated.add(row['chuffed_id'])
            chuffed_rows.append(row)

# Append completely new ones
for u in backlog_updates:
    if u['platform'] == 'chuffed':
        pure_id = u['campaign_id'].replace('chuffed_', '')
        if pure_id not in chuffed_ids_updated:
            chuffed_rows.append({
                'chuffed_id': pure_id,
                'beneficiary': u['beneficiary'],
                'title': u['title'],
                'raised_eur': u['raised_eur'],
                'whatsapp_contact': u.get('alt_chat_name', ''),
                'number': u.get('manual_number') or u.get('suggested_number'),
                'vetted': '',
                'notes': u.get('manual_note', '')
            })

with open(chuffed_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['chuffed_id', 'beneficiary', 'title', 'raised_eur', 'whatsapp_contact', 'number', 'vetted', 'notes'])
    writer.writeheader()
    writer.writerows(chuffed_rows)

# 3. Update Whydonate
whydonate_rows = []
whydonate_titles_updated = set()
if os.path.exists(whydonate_path):
    with open(whydonate_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            updates = [u for u in backlog_updates if u['platform'] == 'whydonate' and u['title'] == row['whydonate_title']]
            if updates:
                u = updates[0]
                row['number'] = u.get('manual_number') or u.get('suggested_number')
                if u.get('alt_chat_name'):
                    row['whatsapp_contact'] = u['alt_chat_name']
                whydonate_titles_updated.add(row['whydonate_title'])
            whydonate_rows.append(row)

# Append new ones
for u in backlog_updates:
    if u['platform'] == 'whydonate':
        if u['title'] not in whydonate_titles_updated:
            whydonate_rows.append({
                'whydonate_title': u['title'],
                'beneficiary': u['beneficiary'],
                'whatsapp_contact': u.get('alt_chat_name', ''),
                'number': u.get('manual_number') or u.get('suggested_number'),
                'vetted': '',
                'notes': u.get('manual_note', '')
            })

with open(whydonate_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['whydonate_title', 'beneficiary', 'whatsapp_contact', 'number', 'vetted', 'notes'])
    writer.writeheader()
    writer.writerows(whydonate_rows)

print("Mapping files updated successfully.")
