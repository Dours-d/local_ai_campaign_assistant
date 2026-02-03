import json
import os

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIFIED_PATH = os.path.join(DATA_DIR, "data", "campaigns_unified.json")
BATCH_PATH = os.path.join(DATA_DIR, "data", "whydonate_batch_create.json")

def sync_internal_names():
    if not os.path.exists(UNIFIED_PATH) or not os.path.exists(BATCH_PATH):
        print("Missing unified or batch file.")
        return

    with open(UNIFIED_PATH, "r", encoding="utf-8") as f:
        unified_data = json.load(f)
    
    with open(BATCH_PATH, "r", encoding="utf-8") as f:
        batch_list = json.load(f)

    # Create a lookup map by ID or Title
    # Unified has 'id' (chuffed_...) and 'title'. Batch has 'chuffed_id' and 'title'.
    unified_map = {}
    for c in unified_data.get("campaigns", []):
        uid = c.get("id")
        if uid: unified_map[uid] = c
    
    updated_count = 0
    
    for item in batch_list:
        # Construct unified ID: "source_id"
        source = item.get("source", "chuffed")
        raw_id = item.get("id")
        created_at = item.get("created_at")
        
        # Try exact construction
        unified_id = f"{source}_{raw_id}"
        
        match = unified_map.get(unified_id)
        
        # Fallback: try finding by title and created_at if ID fails (some might differ)
        if not match:
             for uid, c in unified_map.items():
                 if c.get("title") == item.get("title") and c.get("created_at") == created_at:
                     match = c
                     break
        
        if match:
            privacy = match.get("privacy", {})
            internal_name = privacy.get("internal_name")
            if internal_name:
                # Add to batch item
                if item.get("internal_name") != internal_name:
                    item["internal_name"] = internal_name
                    updated_count += 1
        else:
            # print(f"Warning: No unified match for batch item {unified_id}")
            pass
        
    if updated_count > 0:
        with open(BATCH_PATH, "w", encoding="utf-8") as f:
            json.dump(batch_list, f, indent=2)
        print(f"Synced {updated_count} internal names to batch file.")
    else:
        print("No synced updates needed (names already match).")

if __name__ == "__main__":
    sync_internal_names()
