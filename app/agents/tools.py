from typing import Dict, Any, List
from app.analysis.market_analyzer import MarketAnalyzer
from app.simulation.portfolio import VirtualPortfolio

class AgentTools:
    """Safe, deterministic inspection tools available to the agent during reasoning."""

    @staticmethod
    def get_market_state(market_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Returns the current market indicators and price."""
        return market_snapshot

    @staticmethod
    def get_portfolio_state(portfolio: VirtualPortfolio) -> Dict[str, Any]:
        """Returns the current portfolio balances and performance."""
        return {
            "cash": round(portfolio.cash, 2),
            "portfolio_value": round(portfolio.get_total_portfolio_value(), 2),
            "total_return_pct": portfolio.get_total_return_pct(),
            "realized_pnl": portfolio.get_realized_pnl(),
            "unrealized_pnl": portfolio.get_unrealized_pnl()
        }

    @staticmethod
    def get_open_position(portfolio: VirtualPortfolio, symbol: str) -> Dict[str, Any]:
        """Returns details for a specific stock position."""
        pos = portfolio.get_position(symbol)
        return {
            "symbol": pos.symbol,
            "quantity": pos.quantity,
            "average_entry_price": pos.average_entry_price,
            "market_value": pos.market_value,
            "unrealized_pnl": pos.unrealized_pnl
        }
