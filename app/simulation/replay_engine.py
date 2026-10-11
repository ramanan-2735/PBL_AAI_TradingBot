import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from app.data.models import MarketCandle
from app.analysis.market_analyzer import MarketAnalyzer
from app.simulation.portfolio import VirtualPortfolio
from app.simulation.execution import SimulationEngine
from app.risk.risk_manager import RiskManager
from app.agents.graph import TradingAgentGraph
from app.agents.schemas import AgentState
from app.memory.database import SimulationDatabase
from app.evaluation.metrics import PerformanceEvaluator
from app.config import config

logger = logging.getLogger(__name__)

class HistoricalReplayEngine:
    """Historical Replay Engine strictly preventing Look-Ahead bias.
    Replays candles chronologically: T_1, T_2, ... T_N.
    At step T_k, only candles up to and including T_k are visible to analysis, agent, and portfolio.
    """

    def __init__(
        self,
        candles: List[MarketCandle],
        symbol: str,
        initial_capital: float = 100000.0,
        warmup_period: int = 30,
        slippage_bps: float = 5.0,
        transaction_cost_pct: float = 0.0003,
        db: Optional[SimulationDatabase] = None,
        on_step_callback: Optional[Callable[[dict], None]] = None
    ):
        self.candles = candles
        self.symbol = symbol.upper()
        self.initial_capital = initial_capital
        self.warmup_period = warmup_period
        self.db = db or SimulationDatabase()
        self.on_step_callback = on_step_callback

        # Initialize Simulation components
        self.portfolio = VirtualPortfolio(initial_capital=initial_capital)
        self.risk_manager = RiskManager(
            max_position_pct=config.MAX_POSITION_PCT,
            max_order_pct=config.MAX_ORDER_PCT,
            daily_loss_limit_pct=config.DAILY_LOSS_LIMIT_PCT
        )
        self.simulation_engine = SimulationEngine(
            portfolio=self.portfolio,
            slippage_bps=slippage_bps,
            transaction_cost_pct=transaction_cost_pct
        )
        self.agent_graph = TradingAgentGraph(
            portfolio=self.portfolio,
            risk_manager=self.risk_manager,
            simulation_engine=self.simulation_engine
        )
        self.session_id = f"replay_{uuid.uuid4().hex[:8]}"

    def run(self) -> Dict[str, Any]:
        """Runs the entire replay backtest from candle 0 to N."""
        self.db.record_session(self.session_id, "HISTORICAL_REPLAY", self.symbol, self.initial_capital)

        for i in range(len(self.candles)):
            # Strictly slice history up to the current candle index i (NO LOOK-AHEAD)
            current_candle = self.candles[i]
            history_window = self.candles[:i + 1]

            # Warm-up check
            if len(history_window) < self.warmup_period:
                # Still building indicator history
                self.portfolio.update_market_price(self.symbol, current_candle.close)
                self.portfolio.record_snapshot(current_candle.timestamp)
                continue

            # 1. OBSERVE & ANALYZE using only the historical slice
            market_snapshot = MarketAnalyzer.analyze_window(history_window)

            # 2. Retrieve recent decision context from memory
            recent_decisions = self.db.get_recent_decisions(self.session_id, limit=3)

            # 3. Construct current agent state
            initial_state = AgentState(
                symbol=self.symbol,
                timestamp=current_candle.timestamp.isoformat(),
                current_price=current_candle.close,
                market_snapshot=market_snapshot,
                recent_decisions=recent_decisions
            )

            # 4. Invoke LangGraph Cycle
            final_state = self.agent_graph.run_cycle(initial_state)

            # 5. Persist Decision to Memory
            if final_state.decision:
                risk_res = final_state.risk_result or {}
                self.db.record_decision(
                    session_id=self.session_id,
                    timestamp=final_state.timestamp,
                    symbol=self.symbol,
                    price=final_state.current_price,
                    action=final_state.decision.action,
                    quantity=final_state.decision.quantity,
                    confidence=final_state.decision.confidence,
                    decision_summary=final_state.decision.decision_summary,
                    risk_summary=final_state.decision.risk_summary,
                    risk_approved=risk_res.get("is_approved", False),
                    risk_reason=risk_res.get("reason", ""),
                    raw_indicators=market_snapshot
                )

            # 6. Persist Execution if Trade Occurred
            if final_state.execution_result and "trade_id" in final_state.execution_result:
                self.db.record_trade(self.session_id, final_state.execution_result)

            # 7. Persist Snapshot
            last_snap = self.portfolio.snapshots[-1] if self.portfolio.snapshots else None
            if last_snap:
                self.db.record_snapshot(self.session_id, last_snap.model_dump())

            # 8. Step Callback (for UI or logging)
            if self.on_step_callback:
                self.on_step_callback({
                    "step": i,
                    "total_steps": len(self.candles),
                    "candle": current_candle,
                    "state": final_state,
                    "portfolio_value": self.portfolio.get_total_portfolio_value()
                })

        # Calculate final evaluation
        final_value = self.portfolio.get_total_portfolio_value()
        trades = self.db.get_session_trades(self.session_id)
        snapshots = self.db.get_session_snapshots(self.session_id)
        
        bench_start = self.candles[self.warmup_period - 1].close if len(self.candles) >= self.warmup_period else self.candles[0].close
        bench_end = self.candles[-1].close if self.candles else bench_start

        evaluation = PerformanceEvaluator.evaluate(
            initial_capital=self.initial_capital,
            final_value=final_value,
            trades=trades,
            snapshots=snapshots,
            benchmark_initial_price=bench_start,
            benchmark_final_price=bench_end
        )

        return {
            "session_id": self.session_id,
            "evaluation": evaluation,
            "trades": trades,
            "snapshots": snapshots
        }
