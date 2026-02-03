import csv
import os
from collections import defaultdict

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYSIS_PATH = os.path.join(DATA_DIR, "data", "atomic_fund_analysis.csv")
MAPPING_PATH = os.path.join(DATA_DIR, "data", "pfd_address_mapping.csv")

def load_address_mapping():
    mapping = {}
    if os.path.exists(MAPPING_PATH):
        with open(MAPPING_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # Skip header if present (heuristic)
            header_skipped = False
            for row in reader:
                if not row: continue
                if not header_skipped and row[0] == 'address':
                    header_skipped = True
                    continue
                
                addr = row[0]
                val = row[1] if len(row) > 1 else 'Unknown'
                
                # Clean up "NOT FOUND"
                if val == 'NOT FOUND':
                    val = 'Unknown'
                
                # If duplicate, keep the more informative one? (Last one wins usually)
                mapping[addr] = val
    return mapping

def summarize_beneficiaries():
    if not os.path.exists(ANALYSIS_PATH):
        print(f"File not found: {ANALYSIS_PATH}")
        return

    address_map = load_address_mapping()
    address_stats = defaultdict(lambda: {'count': 0, 'total_amount': 0.0, 'dates': []})
    
    # Store all transactions for detail view
    all_txs = []

    with open(ANALYSIS_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['type'] == 'OUT':
                try:
                    amt = float(row['amount'])
                    addr = row['address']
                    date = row['date']
                    
                    all_txs.append(row)
                    
                    address_stats[addr]['count'] += 1
                    address_stats[addr]['total_amount'] += amt
                    address_stats[addr]['dates'].append(date)
                except ValueError:
                    continue

    print(f"=== TOTAL BENEFICIARY PAYMENTS ANALYSIS ===")
    print(f"Total OUT Transactions: {len(all_txs)}")
    total_out_value = sum(s['total_amount'] for s in address_stats.values())
    print(f"Total Sent: {total_out_value:,.2f} USDT")
    print("-" * 110)
    print(f"{'Address':<40} | {'Beneficiary Name':<35} | {'Count':<5} | {'Total ($)':<15}")
    print("-" * 110)

    # Sort by total amount descending
    sorted_stats = sorted(address_stats.items(), key=lambda x: x[1]['total_amount'], reverse=True)

    for addr, stats in sorted_stats:
        hint = address_map.get(addr, "Unknown")
        # Truncate hint
        if len(hint) > 32:
            hint = hint[:30] + "..."
            
        print(f"{addr:<40} | {hint:<35} | {stats['count']:<5} | {stats['total_amount']:<15,.2f}")

    print("-" * 110)

if __name__ == "__main__":
    summarize_beneficiaries()
