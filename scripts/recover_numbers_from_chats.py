
import os
import json
import re

exports_path = "data/exports"
targets = {
    "Samirah": "Samirah (sue)",
    "Marah": "Marah Ahmad Magde",
    "Youssef": "Youssef (Mahmoud)",
    "Mohammed": "Mohammed (Anas)",
    "Rahaf": "Rahaf Moheeb",
    "Muhammad": "Muhammad (Anas)",
    "Wissam": "Wissam2"
}

results = {}

for filename in os.listdir(exports_path):
    if filename.endswith(".json"):
        with open(os.path.join(exports_path, filename), 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # WhatsApp JSONs usually have 'id', 'name', or 'messages'
                # Let's search the whole JSON string for the names
                json_str = json.dumps(data).lower()
                
                for key, folder_name in targets.items():
                    # Search for parts of the folder name
                    parts = re.findall(r'\b\w+\b', folder_name.lower())
                    if any(p in json_str for p in parts if len(p) > 3):
                        whatsapp_id = data.get('whatsapp_id') or data.get('id') or filename.replace(".json", "")
                        results[key] = whatsapp_id
            except:
                continue

print(json.dumps(results, indent=2))
