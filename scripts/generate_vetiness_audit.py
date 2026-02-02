
import csv
import os
import json
import re

# Paths
checklist_path = "data/vetting_checklist.csv"
gaza_pics_path = r"C:\Users\gaelf\Pictures\GAZA"
output_report = "data/vetting_readiness_report.csv"

def get_folder_readiness(folder_name):
    full_path = os.path.join(gaza_pics_path, folder_name)
    if not os.path.exists(full_path):
        return None
    
    files = os.listdir(full_path)
    file_count = len(files)
    
    # Clues for identification documents
    id_clues = ["id", "identity", "passport", "card", "national", "identite", "carte"]
    found_ids = [f for f in files if any(clue in f.lower() for clue in id_clues)]
    
    # Clue for face/person photo
    face_clues = ["face", "photo", "person", "selfie", "img", "whatsapp image"] # Generics but often person photos
    
    # Clue for campaign proof
    qr_clues = ["qr", "code", "chuffed", "whydonate"]
    found_qrs = [f for f in files if any(clue in f.lower() for clue in qr_clues)]
    
    return {
        "Files": file_count,
        "ID_Proofs": len(found_ids),
        "Campaign_Proofs": len(found_qrs),
        "TopFiles": ", ".join(files[:3])
    }

# 1. Load All Folders
all_folders = [d for d in os.listdir(gaza_pics_path) if os.path.isdir(os.path.join(gaza_pics_path, d))]

# 2. Process Checklist
readiness_rows = []
with open(checklist_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        contact_name = row['whatsapp_contact'].lower()
        beneficiaries = [b.strip().lower() for b in row['beneficiaries'].split(';')]
        
        matched_folders = []
        
        # Try to match folders to this contact/beneficiaries
        for folder in all_folders:
            f_lower = folder.lower()
            # Match if folder contains contact name or any beneficiary name
            if contact_name and contact_name in f_lower:
                matched_folders.append(folder)
            else:
                for ben in beneficiaries:
                    if ben and ben in f_lower:
                        matched_folders.append(folder)
                        break
        
        # Remove duplicates
        matched_folders = list(set(matched_folders))
        
        # Compile stats for matches
        total_files = 0
        total_ids = 0
        total_qrs = 0
        folder_list_str = "; ".join(matched_folders)
        
        for folder in matched_folders:
            stats = get_folder_readiness(folder)
            if stats:
                total_files += stats['Files']
                total_ids += stats['ID_Proofs']
                total_qrs += stats['Campaign_Proofs']
        
        # Scoring Readiness (0 to 100)
        score = 0
        if matched_folders: score += 20
        if total_files > 0: score += 20
        if total_ids > 0: score += 40
        if total_qrs > 0: score += 20
        
        readiness_rows.append({
            "Phone": row['number'],
            "Contact": row['whatsapp_contact'],
            "Vetted": row['vetted'],
            "MatchedFolders": folder_list_str,
            "ID_Proofs": total_ids,
            "Campaign_Proofs": total_qrs,
            "TotalFiles": total_files,
            "ReadinessScore": score,
            "Recommendation": "Ready for Vetting" if score >= 60 else "Missing ID" if matched_folders else "No Folder Found"
        })

# 3. Save Report
fieldnames = ["Phone", "Contact", "Vetted", "MatchedFolders", "ID_Proofs", "Campaign_Proofs", "TotalFiles", "ReadinessScore", "Recommendation"]
with open(output_report, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(readiness_rows)

print(f"Vetting readiness report generated: {output_report}")
print(f"Scanned {len(readiness_rows)} contacts against {len(all_folders)} media folders.")
