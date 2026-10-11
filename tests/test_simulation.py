import pytest
from datetime import datetime
from app.simulation.portfolio import VirtualPortfolio
from app.simulation.execution import SimulationEngine

def test_portfolio_initial_state():
    p = VirtualPortfolio(initial_capital=100000.0)
    assert p.cash == 100000.0
    assert p.get_total_portfolio_value() == 100000.0
    assert p.get_realized_pnl() == 0.0
    assert p.get_unrealized_pnl() == 0.0

def test_simulated_buy_execution_and_accounting():
    p = VirtualPortfolio(initial_capital=100000.0)
    engine = SimulationEngine(portfolio=p, slippage_bps=0.0, transaction_cost_pct=0.0)
    
    trade = engine.execute_order(
        symbol="RELIANCE",
        action="BUY",
        quantity=10,
        market_price=2000.0,
        timestamp=datetime.now(),
        decision_summary="Test Buy"
    )
    
    assert trade is not None
    assert trade.executed_price == 2000.0
    assert trade.quantity == 10
    assert p.cash == 80000.0
    assert p.get_position("RELIANCE").quantity == 10
    assert p.get_position("RELIANCE").average_entry_price == 2000.0

def test_simulated_sell_realized_pnl():
    p = VirtualPortfolio(initial_capital=100000.0)
    engine = SimulationEngine(portfolio=p, slippage_bps=0.0, transaction_cost_pct=0.0)
    
    # Buy 10 @ 2000
    engine.execute_order(
        symbol="RELIANCE", action="BUY", quantity=10, market_price=2000.0, timestamp=datetime.now()
    )
    # Sell 5 @ 2200 (Gain: 5 * 200 = 1000)
    trade_sell = engine.execute_order(
        symbol="RELIANCE", action="SELL", quantity=5, market_price=2200.0, timestamp=datetime.now()
    )
    
    assert trade_sell is not None
    assert trade_sell.realized_pnl == 1000.0
    assert p.cash == 80000.0 + (5 * 2200.0)
    assert p.get_position("RELIANCE").quantity == 5
    assert p.get_realized_pnl() == 1000.0

def test_cannot_sell_more_than_held():
    p = VirtualPortfolio(initial_capital=100000.0)
    engine = SimulationEngine(portfolio=p)
    # Attempt to sell without holding
    trade = engine.execute_order(
        symbol="RELIANCE", action="SELL", quantity=5, market_price=2000.0, timestamp=datetime.now()
    )
    assert trade is None
