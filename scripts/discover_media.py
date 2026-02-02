
import os
import json
import csv
import re

# Paths
gaza_pics_path = r"C:\Users\gaelf\Pictures\GAZA"
unified_path = "data/campaigns_unified.json"
media_map_path = "data/media_mapping.csv"
output_path = "data/media_discovery_report.csv"

# 1. Load Data
with open(unified_path, 'r', encoding='utf-8') as f:
    campaigns = json.load(f).get("campaigns", [])

existing_mapped_folders = set()
if os.path.exists(media_map_path):
    with open(media_map_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing_mapped_folders.add(row['Folder'])

# 2. Get all folders from the actual directory
actual_folders = [d for d in os.listdir(gaza_pics_path) if os.path.isdir(os.path.join(gaza_pics_path, d))]

# 3. Correlation Logic
discovery = []

for folder_name in actual_folders:
    if folder_name in existing_mapped_folders:
        continue # Already known
    
    # Analyze folder contents for metadata clues
    full_path = os.path.join(gaza_pics_path, folder_name)
    files = os.listdir(full_path)
    file_count = len(files)
    
    # Clue 1: QR Codes often have indices or dates
    qr_codes = [f for f in files if "qr-code" in f.lower()]
    
    # Clue 2: Name components
    # Extract names like "Abdallah (Ismael)" -> ["abdallah", "ismael"]
    parts = re.findall(r'\b\w+\b', folder_name.lower())
    
    potential_matches = []
    
    for c in campaigns:
        ben = c['privacy']['first_name'].lower()
        title = c['title'].lower()
        
        score = 0
        if ben in parts: score += 50
        
        # Check if words from the folder name appear in the title
        for p in parts:
            if p in title and len(p) > 3:
                score += 10
        
        if score >= 50:
            potential_matches.append({
                'title': c['title'],
                'id': c['id'],
                'score': score
            })
    
    # Sort matches by score
    potential_matches.sort(key=lambda x: x['score'], reverse=True)
    best_match = potential_matches[0] if potential_matches else None
    
    discovery.append({
        'Folder': folder_name,
        'FileCount': file_count,
        'HasQRCode': "Yes" if qr_codes else "No",
        'BestMatchTitle': best_match['title'] if best_match else "None",
        'MatchID': best_match['id'] if best_match else "",
        'Score': best_match['score'] if best_match else 0,
        'Files': ", ".join(files[:3]) + ("..." if len(files) > 3 else "")
    })

# 4. Save Discovery Report
fieldnames = ['Folder', 'FileCount', 'HasQRCode', 'BestMatchTitle', 'MatchID', 'Score', 'Files']
with open(output_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in discovery:
        writer.writerow(row)

print(f"Media discovery complete. Found {len(discovery)} unmapped folders.")
print(f"Report saved to: {output_path}")
