import json
import os
from datetime import datetime, timedelta

def generate_report():
    unified_file = 'data/campaigns_unified.json'
    batch_file = 'data/whydonate_batch_create.json'
    
    if not os.path.exists(unified_file):
        print("Unified database not found.")
        return

    with open(unified_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Unified data has campaigns under 'campaigns' key
    campaign_list = data.get('campaigns', [])
    summary = data.get('summary', {})
    
    # Also load batch file for creation status
    batch_list = []
    if os.path.exists(batch_file):
        with open(batch_file, 'r', encoding='utf-8') as f:
            batch_list = json.load(f)

    # Filter for the last 48 hours (Weekend activity)
    now = datetime.now()
    weekend_start = now - timedelta(days=2)
    
    weekend_new = []
    ready_for_payout = []
    threshold = 100
    
    # Healthy creation check
    status0_count = len([c for c in batch_list if c.get('status') == 'failed_debug'])
    created_count = len([c for c in batch_list if c.get('status') == 'created_initial'])

    for c in campaign_list:
        raised = c.get('raised_eur', 0)
        
        # Check if created recently
        # (Assuming 'created_at' is in ISO format)
        try:
            created_at = datetime.fromisoformat(c.get('created_at', '').replace('Z', '+00:00'))
            if created_at > weekend_start:
                weekend_new.append(c)
        except:
            pass
            
        # Check threshold
        if raised >= threshold:
            ready_for_payout.append(c)

    print("\n" + "="*40)
    print(f" MONDAY TACTICAL REPORT - {now.strftime('%Y-%m-%d')}")
    print("="*40)
    
    print(f"\n[1] WEEKEND PROGRESS")
    print(f" - New Campaigns Found: {len(weekend_new)}")
    print(f" - Successfully Created (Whydonate): {created_count}")
    print(f" - Infrastructure Blocks (Status 0/429): {status0_count}")
    
    print(f"\n[2] CURRENT DEBT LOAD")
    print(f" - Total Outstanding Debt: €{summary.get('total_raised_eur', 0):,.2f}")
    print(f" - Total Beneficiaries Managed: {summary.get('total_campaigns', 0)}")
    
    print(f"\n[3] PAYOUT STRATEGY (Snowball)")
    print(f" - Ready for Disbursement (>=€{threshold}): {len(ready_for_payout)}")
    # Sort by amount (largest for impact)
    ready_for_payout.sort(key=lambda x: x.get('raised_eur', 0), reverse=True)
    for c in ready_for_payout[:15]:
        print(f"   * €{c['raised_eur']:>7.2f} - {c['title'][:50]}...")

    print("\n" + "="*40)
    print(" ACTION REQUIRED: Update statuses for 'Ready' holders.")
    print("="*40 + "\n")

if __name__ == "__main__":
    generate_report()
