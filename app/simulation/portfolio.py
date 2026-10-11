from datetime import datetime
from typing import Dict, List, Optional
from app.simulation.models import VirtualPosition, PortfolioSnapshot

class VirtualPortfolio:
    """Virtual simulated portfolio enforcing long-only accounting and cash balance constraints."""

    def __init__(self, initial_capital: float = 100000.0, currency: str = "INR"):
        self.initial_capital: float = float(initial_capital)
        self.cash: float = float(initial_capital)
        self.currency: str = currency
        self.positions: Dict[str, VirtualPosition] = {}
        self.snapshots: List[PortfolioSnapshot] = []

    def get_position(self, symbol: str) -> VirtualPosition:
        sym = symbol.upper()
        if sym not in self.positions:
            self.positions[sym] = VirtualPosition(symbol=sym)
        return self.positions[sym]

    def update_market_price(self, symbol: str, price: float):
        sym = symbol.upper()
        if sym in self.positions:
            self.positions[sym].current_price = price

    def get_total_position_value(self) -> float:
        return sum(pos.market_value for pos in self.positions.values())

    def get_total_portfolio_value(self) -> float:
        return round(self.cash + self.get_total_position_value(), 2)

    def get_realized_pnl(self) -> float:
        return round(sum(pos.realized_pnl for pos in self.positions.values()), 2)

    def get_unrealized_pnl(self) -> float:
        return round(sum(pos.unrealized_pnl for pos in self.positions.values()), 2)

    def get_total_pnl(self) -> float:
        return round(self.get_total_portfolio_value() - self.initial_capital, 2)

    def get_total_return_pct(self) -> float:
        if self.initial_capital <= 0:
            return 0.0
        return round((self.get_total_pnl() / self.initial_capital) * 100.0, 2)

    def record_snapshot(self, timestamp: datetime) -> PortfolioSnapshot:
        total_val = self.get_total_portfolio_value()
        pos_val = self.get_total_position_value()
        snap = PortfolioSnapshot(
            timestamp=timestamp,
            cash=round(self.cash, 2),
            positions_value=round(pos_val, 2),
            total_portfolio_value=round(total_val, 2),
            total_pnl=self.get_total_pnl(),
            total_return_pct=self.get_total_return_pct(),
            open_positions_count=len([p for p in self.positions.values() if p.quantity > 0])
        )
        self.snapshots.append(snap)
        return snap
