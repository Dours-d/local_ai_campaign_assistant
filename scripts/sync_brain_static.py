
import os
import shutil
import json

def sync_brain():
    # Paths
    appdata = os.environ.get('APPDATA', '')
    ki_source = os.path.join(appdata, 'antigravity', 'knowledge')
    if not os.path.exists(ki_source):
        ki_source = os.path.join(appdata, 'antigravity', 'brain')
    
    docs_target = 'docs/ki_archive'
    
    if not os.path.exists(ki_source):
        print("Brain source not found.")
        return

    # Clear old archive
    if os.path.exists(docs_target):
        shutil.rmtree(docs_target)
    os.makedirs(docs_target, exist_ok=True)

    print(f"Syncing brain from {ki_source} to {docs_target}...")
    
    ki_list = []
    
    for ki_id in os.listdir(ki_source):
        ki_path = os.path.join(ki_source, ki_id)
        if not os.path.isdir(ki_path): continue
        
        # Load metadata
        meta_path = os.path.join(ki_path, 'metadata.json')
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
        else:
            meta = {"title": ki_id, "summary": "Detailed intelligence item."}
            
        # Create target subfolder
        target_sub = os.path.join(docs_target, ki_id)
        os.makedirs(target_sub, exist_ok=True)
        
        # Copy markdown artifacts
        arts_path = os.path.join(ki_path, 'artifacts') if os.path.exists(os.path.join(ki_path, 'artifacts')) else ki_path
        for file in os.listdir(arts_path):
            if file.endswith('.md'):
                shutil.copy2(os.path.join(arts_path, file), os.path.join(target_sub, file))
        
        ki_list.append({
            "id": ki_id,
            "title": meta.get("title", ki_id),
            "summary": meta.get("summary", "")
        })

    # Save the index for the frontend to read offline
    with open(os.path.join(docs_target, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(ki_list, f, indent=2)

    print("Success. Run 'git push' to make the brain permanent.")

if __name__ == "__main__":
    sync_brain()
