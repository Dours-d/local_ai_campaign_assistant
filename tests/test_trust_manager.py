import pytest
from src.utils.debt_manager import DebtManager
from src.utils.trust_manager import TrustProjection

@pytest.fixture
def mock_manager(tmp_path):
    d = tmp_path / "test.csv"
    content = "Created At,Type,Currency,Amount,Description,Payment Method\n"
    content += '"01/01/2026, 12:00:00","donation","$","1000.00","Shareholder A","card"\n'
    content += '"02/01/2026, 12:00:00","donation","$","500.00","Shareholder B","card"\n'
    d.write_text(content, encoding='utf-8')
    return DebtManager(str(d))

def test_trust_shares(mock_manager):
    engine = TrustProjection(mock_manager)
    stats = engine.get_shareholder_stats()
    
    assert len(stats) == 2
    # A has 2/3 of total debt
    assert stats[0]['shareholder'] == "Shareholder A"
    assert round(stats[0]['trust_share_percent'], 2) == 66.67

def test_trust_projections(mock_manager):
    engine = TrustProjection(mock_manager)
    # $1500 total debt, $500/month velocity
    proj = engine.project_resolution(500.0)
    assert proj['projected_months'] == 3.0
