
import json
import os

def normalize(t):
    import re
    if not t: return ""
    t = str(t).replace('\u00a0', ' ').lower()
    t = re.sub(r'[^a-z0-9 ]', '', t)
    return " ".join(t.split())

def is_similar(t1, t2):
    s1 = normalize(t1)
    s2 = normalize(t2)
    return s1 == s2 or s1 in s2 or s2 in s1

def main():
    chuffed = json.load(open('data/chuffed_campaigns.json', encoding='utf-8'))
    existing = json.load(open('data/whydonate_all_campaigns.json', encoding='utf-8'))
    
    # Also load the previous batch results
    batch_file = 'data/whydonate_batch_create.json'
    batch_created = []
    if os.path.exists(batch_file):
        batch_data = json.load(open(batch_file, encoding='utf-8'))
        batch_created = [c for c in batch_data if c.get('status') == 'created_initial']
    
    existing_titles = [c.get('title', '') for c in existing] + [c.get('title', '') for c in batch_created]
    
    missing = []
    for c in chuffed:
        found = False
        for ext in existing_titles:
            if is_similar(c['title'], ext):
                found = True
                break
        if not found:
            missing.append(c)
            
    print(f"Total Chuffed: {len(chuffed)}")
    print(f"Known on Whydonate (Scraped): {len(existing)}")
    print(f"Recently Created (Not yet scraped): {len(batch_created)}")
    print(f"Truly Missing: {len(missing)}")
    
    for m in missing:
        m['status'] = 'pending_migration'
        
    # Take the next batch of 60
    batch_size = 60
    next_batch = missing[:batch_size]
    
    with open('data/whydonate_batch_create.json', 'w', encoding='utf-8') as f:
        json.dump(next_batch, f, indent=2)
    print(f"Saved {len(next_batch)} truly missing campaigns to data/whydonate_batch_create.json")

if __name__ == '__main__':
    main()
