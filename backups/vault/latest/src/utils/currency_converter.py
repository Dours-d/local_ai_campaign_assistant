from typing import Dict, Optional

class CurrencyConverter:
    """
    Handles currency conversion with a simulated Stripe fee (2.5%).
    Base currency is EUR.
    """
    
    # Static exchange rates (Mocked for now, could be dynamic)
    # 1 EUR = 1.09 USD (approx)
    # 1 USD = 0.92 EUR
    RATES = {
        "EUR": 1.0,
        "USD": 0.92,
        "$": 0.92,
        "€": 1.0,
        "GBP": 1.20,
        "£": 1.20,
        "AED": 0.25,
        "د.إ": 0.25
    }
    
    STRIPE_FX_FEE = 0.025 # 2.5%
    
    @classmethod
    def convert_to_eur(cls, amount: float, currency: str) -> float:
        """Converts an amount to EUR and applies a 2.5% fee if not already in EUR."""
        currency = currency.upper().strip()
        
        if currency in ["EUR", "€"]:
            return amount
        
        rate = cls.RATES.get(currency, 1.0)
        base_eur = amount * rate
        
        # Apply 2.5% fee on foreign exchange
        conversion_fee = base_eur * cls.STRIPE_FX_FEE
        return base_eur - conversion_fee

    @classmethod
    def get_fee(cls, amount: float, currency: str) -> float:
        """Returns the conversion fee applied to the amount in EUR"""
        currency = currency.upper().strip()
        if currency in ["EUR", "€"]:
            return 0.0
            
        rate = cls.RATES.get(currency, 1.0)
        base_eur = amount * rate
        return base_eur * cls.STRIPE_FX_FEE
