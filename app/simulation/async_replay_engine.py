import asyncio
import logging
import uuid
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

class AsyncReplayEngine:
    """Asynchronous Replay Engine designed for live WebSocket streaming to the React frontend.
    Features:
    - Zero look-ahead bias: at time step T, only candles <= T are exposed
    - Warm-up period: starts with warm-up candles, then streams incrementally
    - Accelerated playback: 0.5x, 1x, 2x, 5x, 10x, 25x, 50x, 100x
    - Real-time controls: START, PAUSE, RESUME, STEP, STOP, RESTART
    - Configurable agent decision frequency (default: every 5 candles)
    - Emits fine-grained WebSocket events: candle, agent_status, agent_decision, risk, trade, portfolio_update, simulation_status
    """

    def __init__(
        self,
        candles: List[MarketCandle],
        symbol: str = "RELIANCE",
        initial_capital: float = 100000.0,
        warmup_period: int = 30,
        decision_frequency: int = 5,
        speed_multiplier: float = 25.0,
        slippage_bps: float = 5.0,
        transaction_cost_pct: float = 0.0003,
        db: Optional[SimulationDatabase] = None,
        event_broadcaster: Optional[Callable[[dict], Any]] = None
    ):
        self.candles = candles
        self.symbol = symbol.upper()
        self.initial_capital = initial_capital
        self.warmup_period = min(warmup_period, len(candles) - 1 if len(candles) > 1 else 1)
        self.decision_frequency = decision_frequency
        self.speed_multiplier = speed_multiplier
        self.slippage_bps = slippage_bps
        self.transaction_cost_pct = transaction_cost_pct
        self.db = db or SimulationDatabase()
        self.event_broadcaster = event_broadcaster

        # State management
        self.session_id = f"replay_{uuid.uuid4().hex[:8]}"
        self.current_index = self.warmup_period
        self.status = "IDLE"  # IDLE, RUNNING, PAUSED, COMPLETED, STOPPED
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._stop_requested = False
        self._task: Optional[asyncio.Task] = None

        # Reusable simulation components
        self._init_simulation()

    def _init_simulation(self):
        self.portfolio = VirtualPortfolio(initial_capital=self.initial_capital)
        self.risk_manager = RiskManager(
            max_position_pct=config.MAX_POSITION_PCT,
            max_order_pct=config.MAX_ORDER_PCT,
            daily_loss_limit_pct=config.DAILY_LOSS_LIMIT_PCT
        )
        self.simulation_engine = SimulationEngine(
            portfolio=self.portfolio,
            slippage_bps=self.slippage_bps,
            transaction_cost_pct=self.transaction_cost_pct
        )
        self.agent_graph = TradingAgentGraph(
            portfolio=self.portfolio,
            risk_manager=self.risk_manager,
            simulation_engine=self.simulation_engine
        )
        self.db.record_session(self.session_id, "HISTORICAL_REPLAY", self.symbol, self.initial_capital)

    async def _emit(self, event: dict):
        if self.event_broadcaster:
            try:
                res = self.event_broadcaster(event)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.error(f"Error broadcasting event: {e}")

    def get_warmup_candles(self) -> List[dict]:
        """Returns the initial warm-up batch of candles visible at start."""
        return [{
            "timestamp": c.timestamp.isoformat(),
            "symbol": c.symbol,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume
        } for c in self.candles[:self.warmup_period]]

    def get_current_snapshot(self) -> dict:
        curr_candle = self.candles[self.current_index] if self.current_index < len(self.candles) else self.candles[-1]
        pos = self.portfolio.get_position(self.symbol)
        tot_val = self.portfolio.get_total_portfolio_value()
        return {
            "session_id": self.session_id,
            "status": self.status,
            "current_index": self.current_index,
            "total_candles": len(self.candles),
            "progress_pct": round((self.current_index / max(len(self.candles), 1)) * 100, 1),
            "simulation_timestamp": curr_candle.timestamp.isoformat(),
            "current_price": curr_candle.close,
            "speed": self.speed_multiplier,
            "portfolio": {
                "initial_capital": self.initial_capital,
                "cash": round(self.portfolio.cash, 2),
                "invested": round(pos.market_value, 2),
                "portfolio_value": round(tot_val, 2),
                "total_return_pct": self.portfolio.get_total_return_pct(),
                "realized_pnl": self.portfolio.get_realized_pnl(),
                "unrealized_pnl": pos.unrealized_pnl,
                "holdings": {
                    "symbol": self.symbol,
                    "quantity": pos.quantity,
                    "avg_price": pos.average_entry_price,
                    "current_price": curr_candle.close
                }
            }
        }

    async def start(self):
        if self.status == "RUNNING":
            return
        self.status = "RUNNING"
        self._stop_requested = False
        self._pause_event.set()
        
        # Emit initial status & warm-up event
        await self._emit({
            "type": "simulation_status",
            "status": "RUNNING",
            "session_id": self.session_id,
            "total_candles": len(self.candles),
            "warmup_count": self.warmup_period
        })
        
        self._task = asyncio.create_task(self._run_loop())

    async def pause(self):
        if self.status == "RUNNING":
            self.status = "PAUSED"
            self._pause_event.clear()
            await self._emit({
                "type": "simulation_status",
                "status": "PAUSED",
                "current_index": self.current_index
            })

    async def resume(self):
        if self.status == "PAUSED":
            self.status = "RUNNING"
            self._pause_event.set()
            await self._emit({
                "type": "simulation_status",
                "status": "RUNNING",
                "current_index": self.current_index
            })

    async def step(self):
        """Advances exactly one candle while paused."""
        if self.status == "PAUSED" and self.current_index < len(self.candles):
            await self._process_step(self.current_index)
            self.current_index += 1

    async def stop(self):
        self._stop_requested = True
        self.status = "STOPPED"
        self._pause_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
        await self._emit({
            "type": "simulation_status",
            "status": "STOPPED",
            "current_index": self.current_index
        })

    async def restart(self):
        await self.stop()
        self.current_index = self.warmup_period
        self.session_id = f"replay_{uuid.uuid4().hex[:8]}"
        self._init_simulation()
        self.status = "IDLE"
        await self._emit({
            "type": "simulation_status",
            "status": "RESTARTED",
            "session_id": self.session_id,
            "current_index": self.current_index
        })

    def set_speed(self, speed: float):
        self.speed_multiplier = max(0.5, float(speed))

    async def _run_loop(self):
        try:
            while self.current_index < len(self.candles) and not self._stop_requested:
                await self._pause_event.wait()
                if self._stop_requested:
                    break

                await self._process_step(self.current_index)
                self.current_index += 1

                # Calculate interval delay based on speed multiplier
                # Base real-world candle delay ~ 1.0s scaled down
                base_delay = 1.0 / self.speed_multiplier
                await asyncio.sleep(max(0.01, base_delay))

            if self.current_index >= len(self.candles) and not self._stop_requested:
                self.status = "COMPLETED"
                # Compute final evaluation
                eval_metrics = self._generate_final_evaluation()
                await self._emit({
                    "type": "simulation_completed",
                    "status": "COMPLETED",
                    "session_id": self.session_id,
                    "evaluation": eval_metrics
                })

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Exception in replay loop: {e}", exc_info=True)
            self.status = "ERROR"
            await self._emit({"type": "simulation_error", "error": str(e)})

    async def _process_step(self, idx: int):
        current_candle = self.candles[idx]
        history_window = self.candles[:idx + 1]  # ZERO LOOK-AHEAD

        # Update portfolio market price
        self.portfolio.update_market_price(self.symbol, current_candle.close)

        # 1. Emit candle event
        await self._emit({
            "type": "candle",
            "timestamp": current_candle.timestamp.isoformat(),
            "symbol": current_candle.symbol,
            "open": current_candle.open,
            "high": current_candle.high,
            "low": current_candle.low,
            "close": current_candle.close,
            "volume": current_candle.volume,
            "index": idx,
            "total": len(self.candles)
        })

        # 2. Check if this step triggers agent evaluation
        # Warmup is guaranteed passed since start index >= warmup_period
        should_evaluate_agent = (idx % self.decision_frequency == 0)

        market_snapshot = MarketAnalyzer.analyze_window(history_window)
        # Emit indicator update
        await self._emit({
            "type": "indicators_update",
            "timestamp": current_candle.timestamp.isoformat(),
            "price": current_candle.close,
            "sma_20": market_snapshot.get("sma_20"),
            "sma_50": market_snapshot.get("sma_50"),
            "rsi": market_snapshot.get("rsi"),
            "trend": market_snapshot.get("trend"),
            "strategy_signal": market_snapshot.get("strategy_signal"),
            "strategy_reason": market_snapshot.get("strategy_reason")
        })

        if should_evaluate_agent:
            await self._emit({
                "type": "agent_status",
                "status": "ANALYZING",
                "timestamp": current_candle.timestamp.isoformat()
            })

            recent_decisions = self.db.get_recent_decisions(self.session_id, limit=3)
            initial_state = AgentState(
                symbol=self.symbol,
                timestamp=current_candle.timestamp.isoformat(),
                current_price=current_candle.close,
                market_snapshot=market_snapshot,
                recent_decisions=recent_decisions
            )

            # Invoke LangGraph Agent
            final_state = self.agent_graph.run_cycle(initial_state)

            if final_state.decision:
                # Emit agent decision
                await self._emit({
                    "type": "agent_decision",
                    "timestamp": final_state.timestamp,
                    "action": final_state.decision.action,
                    "symbol": self.symbol,
                    "quantity": final_state.decision.quantity,
                    "confidence": final_state.decision.confidence,
                    "decision_summary": final_state.decision.decision_summary,
                    "risk_summary": final_state.decision.risk_summary,
                    "conditions_to_reconsider": final_state.decision.conditions_to_reconsider
                })

                # Risk check result
                risk_res = final_state.risk_result or {}
                await self._emit({
                    "type": "risk",
                    "status": "APPROVED" if risk_res.get("is_approved") else "REJECTED",
                    "reason": risk_res.get("reason", "Checked"),
                    "action": final_state.decision.action,
                    "symbol": self.symbol,
                    "quantity": final_state.decision.quantity
                })

                # Persist decision to DB
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

                # Simulated trade execution if occurred
                if final_state.execution_result and "trade_id" in final_state.execution_result:
                    tr = final_state.execution_result
                    self.db.record_trade(self.session_id, tr)
                    await self._emit({
                        "type": "trade",
                        "trade_id": tr["trade_id"],
                        "timestamp": tr["timestamp"],
                        "symbol": tr["symbol"],
                        "action": tr["action"],
                        "quantity": tr["quantity"],
                        "price": tr["executed_price"],
                        "requested_price": tr["requested_price"],
                        "fees": tr["fees"],
                        "realized_pnl": tr.get("realized_pnl", 0.0),
                        "decision_summary": tr.get("decision_summary", "")
                    })

        # Record and emit portfolio snapshot
        snap = self.portfolio.record_snapshot(current_candle.timestamp)
        self.db.record_snapshot(self.session_id, snap.model_dump())
        
        pos = self.portfolio.get_position(self.symbol)
        await self._emit({
            "type": "portfolio_update",
            "timestamp": current_candle.timestamp.isoformat(),
            "cash": round(self.portfolio.cash, 2),
            "invested": round(pos.market_value, 2),
            "portfolio_value": round(self.portfolio.get_total_portfolio_value(), 2),
            "total_return_pct": self.portfolio.get_total_return_pct(),
            "realized_pnl": self.portfolio.get_realized_pnl(),
            "unrealized_pnl": pos.unrealized_pnl,
            "holdings_quantity": pos.quantity,
            "average_entry_price": pos.average_entry_price
        })

    def _generate_final_evaluation(self) -> dict:
        final_value = self.portfolio.get_total_portfolio_value()
        trades = self.db.get_session_trades(self.session_id)
        snapshots = self.db.get_session_snapshots(self.session_id)
        bench_start = self.candles[self.warmup_period].close if len(self.candles) > self.warmup_period else self.candles[0].close
        bench_end = self.candles[-1].close if self.candles else bench_start
        return PerformanceEvaluator.evaluate(
            initial_capital=self.initial_capital,
            final_value=final_value,
            trades=trades,
            snapshots=snapshots,
            benchmark_initial_price=bench_start,
            benchmark_final_price=bench_end
        )
