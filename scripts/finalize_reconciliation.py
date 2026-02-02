
import csv
import os

chuffed_map_path = "data/coupling_vetting.csv"
clues_path = "data/media_correlation_clues.csv"

# Load clues
clues = {}
with open(clues_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        clues[row['BestMatch'].replace("chuffed_", "")] = row['Folder']

# Update main map
rows = []
with open(chuffed_map_path, 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

fixes = 0
for r in rows:
    cid = r.get('chuffed_id', '')
    ben = r.get('beneficiary', '')
    num = r.get('number', '')
    
    # Priority fix for the 7 targets
    targets = ["Samirah", "Marah", "Youssef", "Mohammed", "Rahaf", "Muhammad", "Wissam"]
    if any(t.lower() == ben.lower() for t in targets):
        if "@" in num or "x.com" in num or not num:
            r['number'] = "" # Clear invalid numbers
            if cid in clues:
                r['whatsapp_contact'] = clues[cid]
                r['notes'] = f"Media folder: {clues[cid]}. Manual review required for phone number."
                fixes += 1

with open(chuffed_map_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Applied {fixes} specific data fixes to the coupling file.")
