from typing import Dict, Any, List
from .debt_manager import DebtManager

class TrustProjection:
    def __init__(self, manager: DebtManager):
        self.manager = manager

    def get_shareholder_stats(self) -> List[Dict[str, Any]]:
        """
        Calculates the current equity/share for each debt owner.
        """
        shares = self.manager.get_debts_by_shareholder()
        total_debt = sum(shares.values())
        
        stats = []
        for shareholder, amount in shares.items():
            stats.append({
                "shareholder": shareholder,
                "debt_amount": amount,
                "trust_share_percent": (amount / total_debt * 100) if total_debt > 0 else 0,
                "status": "Trustee Candidate"
            })
            
        # Sort by interest (highest first)
        return sorted(stats, key=lambda x: x['debt_amount'], reverse=True)

    def project_resolution(self, monthly_velocity: float) -> Dict[str, Any]:
        """
        Projects how long it will take to resolve all debt based on a monthly resolution velocity.
        """
        total_debt = self.manager.get_total_unsatisfied_debt()
        months_to_resolve = (total_debt / monthly_velocity) if monthly_velocity > 0 else float('inf')
        
        return {
            "total_unsatisfied_debt": total_debt,
            "monthly_velocity": monthly_velocity,
            "projected_months": round(months_to_resolve, 2),
            "system_status": "Active Resolution" if months_to_resolve < float('inf') else "Stagnant"
        }
