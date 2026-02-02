
import csv
import os
import json

# Paths
clues_path = "data/media_correlation_clues.csv"
chuffed_map_path = "data/coupling_vetting.csv"
whydonate_map_path = "data/whydonate_coupling_vetting.csv"

# 1. Load Clues
clues = []
with open(clues_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        clues.append(row)

# 2. Update Chuffed Map
chuffed_rows = []
if os.path.exists(chuffed_map_path):
    with open(chuffed_map_path, 'r', encoding='utf-8') as f:
        chuffed_rows = list(csv.DictReader(f))

# Define the targets we want to fix
targets = ["Samirah", "Marah", "Youssef", "Mohammed", "Rahaf", "Muhammad", "Wissam"]

updated_count = 0

for row in chuffed_rows:
    ben = row.get('beneficiary', '')
    cid = row.get('chuffed_id', '')
    
    # If it's one of our targets and lacks a good number or has invalid data
    is_target = any(t.lower() == ben.lower() for t in targets)
    has_invalid_num = not row.get('number') or "@" in row.get('number') or "x.com" in row.get('number')
    
    if is_target and has_invalid_num:
        # Look for a clue
        for clue in clues:
            # Match by ID or by folder name containing the beneficiary
            clue_id = clue['BestMatch'].replace("chuffed_", "")
            if clue_id == cid:
                # We found a match! Use the folder name as the contact name
                # and flag it for manual number extraction since we only have the folder name
                row['whatsapp_contact'] = clue['Folder']
                row['notes'] = f"Correlated via Pictures/GAZA folder. Needs manual number check."
                updated_count += 1
                break

# 3. Save Chuffed Map
if chuffed_rows:
    with open(chuffed_map_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=chuffed_rows[0].keys())
        writer.writeheader()
        writer.writerows(chuffed_rows)

print(f"Updated {updated_count} Chuffed records with folder-based contact info.")

# 4. Handle Gaps (True Orphans)
# If a clue points to an ID that's NOT in the current mapping file at all, we should add it.
# This fixes the "True Orphans"
existing_ids = {r['chuffed_id'] for r in chuffed_rows}
new_rows = []

for clue in clues:
    cid_pure = clue['BestMatch'].replace("chuffed_", "")
    if "chuffed_" in clue['BestMatch'] and cid_pure not in existing_ids and clue['Score'] >= 100:
        new_rows.append({
            'chuffed_id': cid_pure,
            'beneficiary': clue['Folder'].split(' ')[0],
            'title': clue['Title'],
            'raised_eur': '0', # Unknown here, will be updated by query_db
            'whatsapp_contact': clue['Folder'],
            'number': '',
            'vetted': '',
            'notes': 'Discovered via Pictures/GAZA folder correlation.'
        })

if new_rows:
    with open(chuffed_map_path, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=chuffed_rows[0].keys())
        writer.writerows(new_rows)
    print(f"Added {len(new_rows)} new campaigns discovered in Pictures/GAZA.")
