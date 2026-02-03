
import json

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
    
    existing_titles = [c.get('title', '') for c in existing]
    
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
    print(f"Existing on Whydonate: {len(existing)}")
    print(f"Missing: {len(missing)}")
    
    for m in missing:
        m['status'] = 'pending_migration'
        
    with open('data/whydonate_missing.json', 'w', encoding='utf-8') as f:
        json.dump(missing, f, indent=2)
    print("Saved missing campaigns to data/whydonate_missing.json")

if __name__ == '__main__':
    main()
