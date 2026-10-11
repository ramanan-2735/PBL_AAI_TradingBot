from datetime import datetime
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from app.agents.schemas import AgentState, TradeActionProposal
from app.agents.reasoning import LLMReasoningEngine
from app.risk.risk_manager import RiskManager
from app.simulation.execution import SimulationEngine
from app.simulation.portfolio import VirtualPortfolio

class TradingAgentGraph:
    """Explicit LangGraph workflow orchestrating:
    START -> OBSERVE -> ANALYZE -> REASON -> RISK_CHECK -> SIMULATE -> UPDATE_MEMORY -> END
    """

    def __init__(
        self,
        portfolio: VirtualPortfolio,
        risk_manager: RiskManager,
        simulation_engine: SimulationEngine,
        reasoning_engine: LLMReasoningEngine = None
    ):
        self.portfolio = portfolio
        self.risk_manager = risk_manager
        self.simulation_engine = simulation_engine
        self.reasoning_engine = reasoning_engine or LLMReasoningEngine()
        self.app = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentState)

        # 1. Define nodes
        graph.add_node("observe", self._node_observe)
        graph.add_node("analyze", self._node_analyze)
        graph.add_node("reason", self._node_reason)
        graph.add_node("risk_check", self._node_risk_check)
        graph.add_node("simulate", self._node_simulate)

        # 2. Define edges
        graph.set_entry_point("observe")
        graph.add_edge("observe", "analyze")
        graph.add_edge("analyze", "reason")
        graph.add_edge("reason", "risk_check")
        graph.add_edge("risk_check", "simulate")
        graph.add_edge("simulate", END)

        return graph.compile()

    def _node_observe(self, state: AgentState) -> dict:
        # Update current price in portfolio
        self.portfolio.update_market_price(state.symbol, state.current_price)
        pos = self.portfolio.get_position(state.symbol)
        
        portfolio_summary = {
            "cash": round(self.portfolio.cash, 2),
            "portfolio_value": round(self.portfolio.get_total_portfolio_value(), 2),
            "total_return_pct": self.portfolio.get_total_return_pct(),
            "realized_pnl": self.portfolio.get_realized_pnl(),
            "unrealized_pnl": self.portfolio.get_unrealized_pnl()
        }

        position_summary = {
            "symbol": pos.symbol,
            "quantity": pos.quantity,
            "average_entry_price": pos.average_entry_price,
            "market_value": pos.market_value,
            "unrealized_pnl": pos.unrealized_pnl
        }

        return {
            "portfolio_summary": portfolio_summary,
            "cycle_status": "OBSERVED"
        }

    def _node_analyze(self, state: AgentState) -> dict:
        # Technical indicators inspection
        tool_outputs = {
            "market_summary": state.market_snapshot,
            "portfolio_summary": state.portfolio_summary
        }
        return {
            "tool_outputs": tool_outputs,
            "cycle_status": "ANALYZED"
        }

    def _node_reason(self, state: AgentState) -> dict:
        pos = self.portfolio.get_position(state.symbol)
        context = {
            "symbol": state.symbol,
            "market_snapshot": state.market_snapshot,
            "portfolio_summary": state.portfolio_summary,
            "position": {
                "quantity": pos.quantity,
                "average_entry_price": pos.average_entry_price,
                "unrealized_pnl": pos.unrealized_pnl,
                "market_value": pos.market_value
            },
            "recent_decisions": state.recent_decisions
        }
        proposal = self.reasoning_engine.reason(context)
        return {
            "decision": proposal,
            "cycle_status": "DECIDED"
        }

    def _node_risk_check(self, state: AgentState) -> dict:
        if not state.decision:
            return {"cycle_status": "RISK_SKIPPED"}

        ts = datetime.fromisoformat(state.timestamp) if isinstance(state.timestamp, str) else datetime.now()
        risk_res = self.risk_manager.evaluate_order(
            portfolio=self.portfolio,
            symbol=state.symbol,
            action=state.decision.action,
            quantity=state.decision.quantity,
            market_price=state.current_price,
            timestamp=ts
        )

        return {
            "risk_result": risk_res.model_dump(),
            "cycle_status": "RISK_CHECKED"
        }

    def _node_simulate(self, state: AgentState) -> dict:
        ts = datetime.fromisoformat(state.timestamp) if isinstance(state.timestamp, str) else datetime.now()
        
        # Only execute if approved by Risk Manager and action is BUY or SELL
        if state.risk_result and state.risk_result.get("is_approved") and state.decision and state.decision.action in ["BUY", "SELL"]:
            trade = self.simulation_engine.execute_order(
                symbol=state.symbol,
                action=state.decision.action,
                quantity=state.decision.quantity,
                market_price=state.current_price,
                timestamp=ts,
                decision_summary=state.decision.decision_summary,
                risk_summary=state.decision.risk_summary
            )
            # Record portfolio snapshot
            self.portfolio.record_snapshot(ts)
            return {
                "execution_result": trade.model_dump() if trade else {"status": "EXECUTION_REJECTED_BY_ENGINE"},
                "cycle_status": "SIMULATED"
            }
        
        # If HOLD or rejected, still record snapshot
        self.portfolio.record_snapshot(ts)
        return {
            "execution_result": {"status": "NO_ORDER_EXECUTED", "action": state.decision.action if state.decision else "NONE"},
            "cycle_status": "CYCLE_COMPLETED"
        }

    def run_cycle(self, initial_state: AgentState) -> AgentState:
        result_dict = self.app.invoke(initial_state)
        return AgentState(**result_dict)
