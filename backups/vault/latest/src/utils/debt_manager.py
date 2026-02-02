import csv
import os
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
from .currency_converter import CurrencyConverter

class HistoricalDonation:
    def __init__(self, timestamp: datetime, amount: float, currency: str, shareholder: str, status: str = "unsatisfied"):
        self.timestamp = timestamp
        self.amount = amount
        self.currency = currency
        self.shareholder = shareholder
        self.status = status # unsatisfied, partially_resolved, resolved
        
        # Convert to EUR (Main project currency)
        self.amount_eur = CurrencyConverter.convert_to_eur(amount, currency)
        self.fx_fee_eur = CurrencyConverter.get_fee(amount, currency)
        self.remaining_amount = self.amount_eur

class DebtManager:
    """
    Manages historical debt based on CSV datasets.
    Priority is strictly based on donation timestamp (FIFO).
    """
    
    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path
        self.donations: List[HistoricalDonation] = []
        self._load_dataset()

    def _load_dataset(self):
        if not os.path.exists(self.dataset_path):
            print(f"DEBUG: Dataset path does not exist: {self.dataset_path}")
            return

        with open(self.dataset_path, mode='r', encoding='utf-8') as f:
            # Check for Byte Order Mark (BOM) which can happen in Excel-saved CSVs
            first_char = f.read(1)
            if first_char != '\ufeff':
                f.seek(0)
                
            reader = csv.DictReader(f)
            # Log fieldnames for debugging
            # print(f"DEBUG: CSV Fieldnames found: {reader.fieldnames}")
            
            for row in reader:
                if row.get('Type', '').lower() != 'donation':
                    continue
                
                try:
                    # Stripping quotes if they weren't handled by DictReader
                    date_val = row['Created At'].strip('" ')
                    amount_val = row['Amount'].strip('" ')
                    
                    ts = datetime.strptime(date_val, "%d/%m/%Y, %H:%M:%S")
                    amount = float(amount_val)
                    
                    self.donations.append(HistoricalDonation(
                        timestamp=ts,
                        amount=amount,
                        currency=row['Currency'],
                        shareholder=row['Description']
                    ))
                except Exception as e:
                    # print(f"DEBUG: Failed to parse row: {row}. Error: {e}")
                    continue
        
        # Sort by timestamp (Oldest first for resolution priority)
        self.donations.sort(key=lambda x: x.timestamp)
        # print(f"DEBUG: Loaded {len(self.donations)} donations.")

    def get_total_unsatisfied_debt(self) -> float:
        """Sum of all remaining amounts in EUR"""
        return sum(d.remaining_amount for d in self.donations if d.status != "resolved")

    def get_debts_by_shareholder(self) -> Dict[str, float]:
        """Aggregates total debt per shareholder (campaign description)"""
        shares = {}
        for d in self.donations:
            if d.status == "resolved":
                continue
            shares[d.shareholder] = shares.get(d.shareholder, 0.0) + d.remaining_amount
        return shares

    def get_priority_queue(self) -> List[HistoricalDonation]:
        """Returns unsatisfied donations sorted by timestamp (FIFO)"""
        return [d for d in self.donations if d.status != "resolved"]

    def resolve_debt(self, amount: float) -> List[Dict[str, Any]]:
        """
        Applies a resolution amount to the oldest debts.
        Returns a list of resolutions performed.
        """
        resolutions = []
        remaining_to_resolve = amount
        
        for d in self.get_priority_queue():
            if remaining_to_resolve <= 0:
                break
                
            applied = min(remaining_to_resolve, d.remaining_amount)
            d.remaining_amount -= applied
            remaining_to_resolve -= applied
            
            if d.remaining_amount <= 0:
                d.status = "resolved"
            else:
                d.status = "partially_resolved"
                
            resolutions.append({
                "shareholder": d.shareholder,
                "amount": applied,
                "timestamp": d.timestamp.isoformat(),
                "status": d.status
            })
            
        return resolutions
