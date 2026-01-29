import pytest
from datetime import datetime
from src.utils.debt_manager import DebtManager, HistoricalDonation
import os

@pytest.fixture
def sample_csv(tmp_path):
    d = tmp_path / "test_donations.csv"
    content = "Created At,Type,Currency,Amount,Description,Payment Method\n"
    content += '"01/01/2026, 12:00:00","donation","$","100.00","Test Shareholder A","card"\n'
    content += '"02/01/2026, 12:00:00","donation","$","50.00","Test Shareholder B","card"\n'
    content += '"03/01/2026, 12:00:00","other","$","10.00","Not a donation","card"\n'
    d.write_text(content, encoding='utf-8')
    return str(d)

def test_debt_manager_loading(sample_csv):
    manager = DebtManager(sample_csv)
    assert len(manager.donations) == 2
    assert manager.donations[0].amount == 100.0
    assert manager.donations[0].shareholder == "Test Shareholder A"

def test_debt_manager_priority(sample_csv):
    manager = DebtManager(sample_csv)
    # 01/01 should come before 02/01
    assert manager.donations[0].timestamp < manager.donations[1].timestamp

def test_debt_resolution(sample_csv):
    manager = DebtManager(sample_csv)
    # Resolve $120
    resolutions = manager.resolve_debt(120.0)
    
    # Resolves all of A ($100) and $20 of B
    assert len(resolutions) == 2
    assert resolutions[0]['amount'] == 100.0
    assert resolutions[0]['status'] == "resolved"
    assert resolutions[1]['amount'] == 20.0
    assert resolutions[1]['status'] == "partially_resolved"
    
    assert manager.get_total_unsatisfied_debt() == 30.0 # 150 - 120
