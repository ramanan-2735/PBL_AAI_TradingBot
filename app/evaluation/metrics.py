import math
from typing import List, Dict, Any, Optional
from app.simulation.models import SimulatedTrade, PortfolioSnapshot

class PerformanceEvaluator:
    """Computes quantitative performance metrics and compares against Buy & Hold benchmark."""

    @staticmethod
    def evaluate(
        initial_capital: float,
        final_value: float,
        trades: List[Dict[str, Any]],
        snapshots: List[Dict[str, Any]],
        benchmark_initial_price: Optional[float] = None,
        benchmark_final_price: Optional[float] = None
    ) -> Dict[str, Any]:
        total_pnl = round(final_value - initial_capital, 2)
        total_return_pct = round((total_pnl / initial_capital) * 100.0, 2) if initial_capital > 0 else 0.0

        # Trade analytics
        closed_trades = [t for t in trades if t.get("action") == "SELL"]
        total_trades = len(trades)
        winning_trades = len([t for t in closed_trades if float(t.get("realized_pnl", 0)) > 0])
        losing_trades = len([t for t in closed_trades if float(t.get("realized_pnl", 0)) < 0])
        win_rate = round((winning_trades / len(closed_trades)) * 100.0, 2) if closed_trades else 0.0

        gross_profit = sum(float(t.get("realized_pnl", 0)) for t in closed_trades if float(t.get("realized_pnl", 0)) > 0)
        gross_loss = abs(sum(float(t.get("realized_pnl", 0)) for t in closed_trades if float(t.get("realized_pnl", 0)) < 0))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (round(gross_profit, 2) if gross_profit > 0 else 0.0)

        # Max Drawdown from equity snapshots
        max_drawdown_pct = 0.0
        peak = initial_capital
        equity_series = [initial_capital] + [s["total_portfolio_value"] for s in snapshots]
        for val in equity_series:
            if val > peak:
                peak = val
            dd = (peak - val) / peak if peak > 0 else 0.0
            if dd > max_drawdown_pct:
                max_drawdown_pct = dd
        max_drawdown_pct = round(max_drawdown_pct * 100.0, 2)

        # Sharpe ratio approximation
        sharpe_ratio = "Insufficient data"
        if len(equity_series) > 10:
            returns = [(equity_series[i] - equity_series[i - 1]) / equity_series[i - 1] for i in range(1, len(equity_series))]
            mean_ret = sum(returns) / len(returns)
            variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
            std_dev = math.sqrt(variance)
            if std_dev > 0:
                # Annualized factor (sqrt(252 * 375))
                sharpe = (mean_ret / std_dev) * math.sqrt(252)
                sharpe_ratio = round(sharpe, 2)

        # Benchmark Comparison: Buy and Hold
        benchmark_return_pct = None
        alpha_pct = None
        if benchmark_initial_price and benchmark_final_price and benchmark_initial_price > 0:
            benchmark_return_pct = round(((benchmark_final_price - benchmark_initial_price) / benchmark_initial_price) * 100.0, 2)
            alpha_pct = round(total_return_pct - benchmark_return_pct, 2)

        return {
            "initial_capital": initial_capital,
            "final_portfolio_value": round(final_value, 2),
            "total_pnl": total_pnl,
            "total_return_pct": total_return_pct,
            "total_trades": total_trades,
            "closed_trades": len(closed_trades),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_drawdown_pct,
            "sharpe_ratio": sharpe_ratio,
            "benchmark_return_pct": benchmark_return_pct,
            "alpha_pct": alpha_pct
        }
