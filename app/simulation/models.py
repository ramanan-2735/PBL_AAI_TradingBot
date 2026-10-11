from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class VirtualPosition(BaseModel):
    symbol: str
    quantity: int = 0
    average_entry_price: float = 0.0
    current_price: float = 0.0
    realized_pnl: float = 0.0

    @property
    def market_value(self) -> float:
        return round(self.quantity * self.current_price, 2)

    @property
    def unrealized_pnl(self) -> float:
        if self.quantity <= 0:
            return 0.0
        return round((self.current_price - self.average_entry_price) * self.quantity, 2)

    @property
    def total_pnl(self) -> float:
        return round(self.realized_pnl + self.unrealized_pnl, 2)


class SimulatedTrade(BaseModel):
    trade_id: str
    timestamp: datetime
    symbol: str
    action: str  # BUY or SELL
    quantity: int
    requested_price: float
    executed_price: float
    slippage: float
    fees: float
    total_cost: float
    realized_pnl: float = 0.0
    decision_summary: str = ""
    risk_summary: str = ""


class PortfolioSnapshot(BaseModel):
    timestamp: datetime
    cash: float
    positions_value: float
    total_portfolio_value: float
    total_pnl: float
    total_return_pct: float
    open_positions_count: int
