import json

batch_file = 'data/whydonate_batch_create.json'
with open(batch_file, 'r', encoding='utf-8') as f:
    campaigns = json.load(f)

for c in campaigns:
    if 'Haytham' in c['title']:
        print(f"Resetting Haytham: {c['title']}")
        c['status'] = 'pending_migration'
    if 'Marah' in c['title']:
        # User said they deleted the double, but let's mark it as created_initial since one exists
        print(f"Ensuring Marah is marked created: {c['title']}")
        c['status'] = 'created_initial'

with open(batch_file, 'w', encoding='utf-8') as f:
    json.dump(campaigns, f, indent=2)
print("Updated statuses in whydonate_batch_create.json")
