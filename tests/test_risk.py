import pytest
from datetime import datetime
from app.simulation.portfolio import VirtualPortfolio
from app.risk.risk_manager import RiskManager

def test_risk_manager_buy_approval_and_rejections():
    p = VirtualPortfolio(initial_capital=100000.0)
    risk = RiskManager(max_position_pct=0.25, max_order_pct=0.10)

    # 1. Valid order: 5 shares @ 1000 = 5000 (5% <= 10% limit) -> APPROVED
    res1 = risk.evaluate_order(
        portfolio=p, symbol="TCS", action="BUY", quantity=5, market_price=1000.0, timestamp=datetime.now()
    )
    assert res1.is_approved is True

    # 2. Excessive order size: 20 shares @ 1000 = 20000 (20% > 10% limit) -> REJECTED
    res2 = risk.evaluate_order(
        portfolio=p, symbol="TCS", action="BUY", quantity=20, market_price=1000.0, timestamp=datetime.now()
    )
    assert res2.is_approved is False
    assert "exceeds max order limit" in res2.reason

    # 3. Insufficient cash -> REJECTED
    p.cash = 500.0
    res3 = risk.evaluate_order(
        portfolio=p, symbol="TCS", action="BUY", quantity=5, market_price=1000.0, timestamp=datetime.now()
    )
    assert res3.is_approved is False
    assert "Insufficient virtual cash" in res3.reason

def test_risk_manager_sell_rejection_when_not_held():
    p = VirtualPortfolio(initial_capital=100000.0)
    risk = RiskManager()
    
    # Sell without holding shares -> REJECTED
    res = risk.evaluate_order(
        portfolio=p, symbol="INFY", action="SELL", quantity=10, market_price=1500.0, timestamp=datetime.now()
    )
    assert res.is_approved is False
    assert "Virtual holdings available: 0" in res.reason
