import pytest
from src.utils.liquidity import LiquidityManager

def test_liquidity_split():
    # Pass None for dataset_path to skip loading the real CSV
    manager = LiquidityManager(dataset_path=None)
    
    # Test $10,000 goal
    split = manager.calculate_split("$10,000")
    
    assert split['gross_goal'] == 10000.0
    assert split['debt_resolution'] == 1000.0 # 10%
    assert split['transaction_fees'] == 500.0  # 5%
    assert split['operational_cushion'] == 1000.0 # 10%
    assert split['net_support'] == 7500.0 # 75%

def test_amount_parsing():
    assert LiquidityManager.parse_amount("€5.000,00") == 5000.0
    assert LiquidityManager.parse_amount("$100") == 100.0
    assert LiquidityManager.parse_amount("Free") == 0.0
