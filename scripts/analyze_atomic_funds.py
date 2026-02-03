import csv
import json
import os
from datetime import datetime, timedelta

atomic_log_path = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\atomic_wallet_log\history-atomicwallet-02.02.2026.csv'
output_path = r'c:\Users\gaelf\Documents\GitHub\local_ai_campaign_assistant\data\atomic_fund_analysis.csv'

def parse_date(date_str):
    # Example: "20 January 2026 at 17:38:45 WET"
    # Remove " WET" and other timezones if present
    date_str = date_str.split(' at ')[0] + ' ' + date_str.split(' at ')[1].split(' ')[0]
    return datetime.strptime(date_str, '%d %B %Y %H:%M:%S')

# Better date parser for the specific format
def parse_atomic_date(date_str):
    try:
        # Example: "24 January 2026 at 22:58:43 WET"
        parts = date_str.strip().split(' ')
        # parts: ['24', 'January', '2026', 'at', '22:58:43', 'WET']
        day = parts[0]
        month = parts[1]
        year = parts[2]
        time = parts[4]
        dt_str = f"{day} {month} {year} {time}"
        return datetime.strptime(dt_str, '%d %B %Y %H:%M:%S')
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return None

transactions = []
with open(atomic_log_path, mode='r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        dt = parse_atomic_date(row['DATE'])
        if not dt: continue
        
        # IN transaction
        if row.get('INAMOUNT') and row.get('INAMOUNT') != '-' and row.get('INCURRENCY') == 'TRX-USDT':
            transactions.append({
                'type': 'IN',
                'amount': float(row['INAMOUNT']),
                'date': dt,
                'txid': row['INTXID'],
                'address': row['ADDRESSTO'] # In logs, ADDRESSTO is often the wallet itself for IN?
            })
        
        # OUT transaction
        if row.get('OUTAMOUNT') and row.get('OUTAMOUNT') != '-' and row.get('OUTCURRENCY') == 'TRX-USDT':
            transactions.append({
                'type': 'OUT',
                'amount': float(row['OUTAMOUNT']),
                'date': dt,
                'txid': row['ORDERID'], # Logs use ORDERID or INTXID differently
                'address': row['ADDRESSTO']
            })

# Sort by date
transactions.sort(key=lambda x: x['date'])

# Analyze coupling
results = []
for i, tx in enumerate(transactions):
    if tx['type'] == 'OUT':
        # Check if there was an IN transaction within 12 hours before
        coupled = False
        coupling_tx = None
        for j in range(i-1, -1, -1):
            prev_tx = transactions[j]
            if prev_tx['type'] == 'IN':
                time_diff = tx['date'] - prev_tx['date']
                if time_diff < timedelta(hours=12):
                    coupled = True
                    coupling_tx = prev_tx
                    break
                else:
                    # Since it's sorted, any further back will also be > 12h
                    break
        
        tx['coupled'] = coupled
        tx['coupling_info'] = f"Coupled with {coupling_tx['amount']} IN at {coupling_tx['date']}" if coupled else "NOT COUPLED"
        results.append(tx)

with open(output_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['date', 'type', 'amount', 'address', 'coupled', 'coupling_info', 'txid'])
    writer.writeheader()
    for res in results:
        writer.writerow(res)

print(f"Analysis finished. Saved to {output_path}")
print(f"Total OUT transactions: {len(results)}")
print(f"Not coupled (Potential Personal Funds): {len([r for r in results if not r['coupled']])}")
