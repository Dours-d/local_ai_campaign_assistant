
import json

def main():
    path = 'data/whydonate_batch_create.json'
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    count = 0
    for c in data:
        if c.get('status') == 'failed_debug':
            c['status'] = 'pending_migration'
            count += 1
            
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"Reset {count} campaigns to pending_migration.")

if __name__ == '__main__':
    main()
