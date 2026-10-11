import uuid
from datetime import datetime
from typing import Optional
from app.simulation.models import SimulatedTrade
from app.simulation.portfolio import VirtualPortfolio
from app.config import config

class SimulationEngine:
    """Dedicated virtual execution engine applying realistic slippage and broker/exchange fees.
    NO REAL BROKER ORDERS WILL EVER BE EXECUTED.
    """

    def __init__(
        self,
        portfolio: VirtualPortfolio,
        slippage_bps: float = 5.0,        # 5 bps = 0.05%
        transaction_cost_pct: float = 0.0003 # 0.03% exchange turnover + STT approx
    ):
        self.portfolio = portfolio
        self.slippage_bps = slippage_bps
        self.transaction_cost_pct = transaction_cost_pct
        self.trades: list[SimulatedTrade] = []

    def execute_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        market_price: float,
        timestamp: datetime,
        decision_summary: str = "",
        risk_summary: str = ""
    ) -> Optional[SimulatedTrade]:
        """Executes a virtual BUY or SELL against the simulated portfolio."""
        action = action.upper().strip()
        sym = symbol.upper().strip()
        pos = self.portfolio.get_position(sym)

        if action not in ["BUY", "SELL"]:
            return None
        if quantity <= 0 or market_price <= 0:
            return None

        # Calculate slippage
        # BUY orders experience upward slippage, SELL downward
        slippage_mult = (self.slippage_bps / 10000.0)
        if action == "BUY":
            executed_price = round(market_price * (1.0 + slippage_mult), 2)
        else:
            executed_price = round(market_price * (1.0 - slippage_mult), 2)

        gross_value = executed_price * quantity
        fees = round(gross_value * self.transaction_cost_pct, 2)
        slippage_val = round(abs(executed_price - market_price) * quantity, 2)
        trade_id = f"sim_{uuid.uuid4().hex[:8]}"

        if action == "BUY":
            total_required = gross_value + fees
            if self.portfolio.cash < total_required:
                return None  # Safety fallback: not enough virtual cash

            # Deduct cash
            self.portfolio.cash -= total_required

            # Update position (weighted average cost basis)
            new_qty = pos.quantity + quantity
            new_cost = (pos.average_entry_price * pos.quantity) + gross_value
            pos.average_entry_price = round(new_cost / new_qty, 2)
            pos.quantity = new_qty
            pos.current_price = market_price

            trade = SimulatedTrade(
                trade_id=trade_id,
                timestamp=timestamp,
                symbol=sym,
                action="BUY",
                quantity=quantity,
                requested_price=market_price,
                executed_price=executed_price,
                slippage=slippage_val,
                fees=fees,
                total_cost=round(total_required, 2),
                realized_pnl=0.0,
                decision_summary=decision_summary,
                risk_summary=risk_summary
            )
            self.trades.append(trade)
            return trade

        elif action == "SELL":
            if pos.quantity < quantity:
                return None  # Safety fallback: cannot sell more than held

            net_proceeds = gross_value - fees
            self.portfolio.cash += net_proceeds

            # Calculate realized P&L on the sold shares
            cost_basis = pos.average_entry_price * quantity
            realized_pnl = round(gross_value - cost_basis - fees, 2)
            pos.realized_pnl += realized_pnl

            # Reduce quantity
            pos.quantity -= quantity
            if pos.quantity == 0:
                pos.average_entry_price = 0.0
            pos.current_price = market_price

            trade = SimulatedTrade(
                trade_id=trade_id,
                timestamp=timestamp,
                symbol=sym,
                action="SELL",
                quantity=quantity,
                requested_price=market_price,
                executed_price=executed_price,
                slippage=slippage_val,
                fees=fees,
                total_cost=round(gross_value, 2),
                realized_pnl=realized_pnl,
                decision_summary=decision_summary,
                risk_summary=risk_summary
            )
            self.trades.append(trade)
            return trade
