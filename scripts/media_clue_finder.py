
import os
import csv
import json
import re

path = r"C:\Users\gaelf\Pictures\GAZA"
unified_path = "data/campaigns_unified.json"
media_map_path = "data/media_mapping.csv"

# Load campaigns
with open(unified_path, 'r', encoding='utf-8') as f:
    campaign_list = json.load(f).get("campaigns", [])

# Load mapped folders to avoid them
mapped_info = {}
if os.path.exists(media_map_path):
    with open(media_map_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapped_info[row['Folder']] = row

# Get all folders
all_folders = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]

# The "Invalid" list names for priority matching
target_names = ["Samirah", "Marah", "Youssef", "Mohammed", "Rahaf", "Muhammad", "Wissam"]

print(f"Analyzing {len(all_folders)} folders...")

potential_correlations = []

for folder in all_folders:
    # If not mapped OR confidence is low/medium
    is_mapped_high = folder in mapped_info and mapped_info[folder].get('Confidence') == 'High'
    
    # We want to look at everything else
    if is_mapped_high:
        continue
        
    full_folder_path = os.path.join(path, folder)
    files = os.listdir(full_folder_path)
    
    # Check for ID clues in filenames
    found_ids = []
    for f in files:
        # Check for 6-digit numbers (common Chuffed IDs are like 123456)
        matches = re.findall(r'\b(\d{6})\b', f)
        for m in matches:
            found_ids.append(m)
            
    # Name matching
    score_board = []
    for c in campaign_list:
        score = 0
        cid_pure = c['id'].replace("chuffed_", "")
        
        # Handle cases where privacy or first_name might be None
        privacy = c.get('privacy', {})
        ben = (privacy.get('first_name') or "").lower()
        title = (c.get('title') or "").lower()
        
        # Folder name match
        if ben and ben in folder.lower(): score += 40
        if cid_pure in folder: score += 100
        
        # Filename ID match
        if cid_pure in found_ids: score += 120 # Found the ID inside the folder!
        
        if score > 0:
            score_board.append({"id": c['id'], "score": score, "title": c['title']})

    if score_board:
        score_board.sort(key=lambda x: x['score'], reverse=True)
        best = score_board[0]
        potential_correlations.append({
            "Folder": folder,
            "BestMatch": best['id'],
            "Score": best['score'],
            "Title": best['title'],
            "Confidence": "Manual Needed" if best['score'] < 100 else "High (Clue found)",
            "Files": ", ".join(files[:2])
        })

# Save results
with open("data/media_correlation_clues.csv", 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=["Folder", "BestMatch", "Score", "Confidence", "Title", "Files"])
    writer.writeheader()
    writer.writerows(potential_correlations)

print(f"Found {len(potential_correlations)} potential clues for unmapped media.")
