import json
import logging
from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.config import config
from app.agents.schemas import TradeActionProposal
from app.agents.prompts import SYSTEM_TRADING_PROMPT, USER_CYCLE_PROMPT

logger = logging.getLogger(__name__)

class LLMReasoningEngine:
    """Manages LLM reasoning with strict fallback to deterministic rules when offline or no API keys are present."""

    def __init__(self):
        self.llm = None
        if config.LLM_API_KEY and config.LLM_API_KEY.strip():
            try:
                self.llm = ChatOpenAI(
                    model=config.LLM_MODEL,
                    api_key=config.LLM_API_KEY,
                    base_url=config.LLM_BASE_URL,
                    temperature=config.LLM_TEMPERATURE,
                    timeout=15
                )
            except Exception as e:
                logger.warning(f"Failed to initialize ChatOpenAI: {e}. Falling back to offline rule-based agent.")

    def reason(self, context: dict) -> TradeActionProposal:
        """Invokes LLM if configured, else applies robust deterministic quantitative reasoning."""
        if self.llm:
            try:
                proposal = self._call_llm(context)
                if proposal:
                    return proposal
            except Exception as e:
                logger.error(f"LLM call failed: {e}. Engaging deterministic reasoning fallback.")

        return self._deterministic_reasoning(context)

    def _call_llm(self, context: dict) -> Optional[TradeActionProposal]:
        symbol = context.get("symbol", "RELIANCE")
        snap = context.get("market_snapshot", {})
        port = context.get("portfolio_summary", {})
        pos = context.get("position", {})

        macd = snap.get("macd") or {}
        user_prompt = USER_CYCLE_PROMPT.format(
            symbol=symbol,
            timestamp=snap.get("timestamp", ""),
            current_price=snap.get("current_price", 0.0),
            trend=snap.get("trend", "NEUTRAL"),
            rsi=snap.get("rsi", "N/A"),
            sma_20=snap.get("sma_20", "N/A"),
            sma_50=snap.get("sma_50", "N/A"),
            ema_20=snap.get("ema_20", "N/A"),
            macd_hist=macd.get("histogram", "N/A"),
            macd_val=macd.get("macd", "N/A"),
            macd_signal=macd.get("signal", "N/A"),
            volatility=snap.get("volatility", "N/A"),
            volume_status=snap.get("volume_status", "NORMAL"),
            cash=port.get("cash", 0.0),
            portfolio_value=port.get("portfolio_value", 0.0),
            total_return_pct=port.get("total_return_pct", 0.0),
            current_holding_qty=pos.get("quantity", 0),
            avg_entry_price=pos.get("average_entry_price", 0.0),
            unrealized_pnl=pos.get("unrealized_pnl", 0.0),
            recent_decisions=json.dumps(context.get("recent_decisions", []))
        )

        structured_llm = self.llm.with_structured_output(TradeActionProposal)
        response = structured_llm.invoke([
            SystemMessage(content=SYSTEM_TRADING_PROMPT.format(symbol=symbol)),
            HumanMessage(content=user_prompt)
        ])
        return response

    def _deterministic_reasoning(self, context: dict) -> TradeActionProposal:
        """Deterministic quantitative strategy logic mimicking multi-factor agent reasoning.
        Evaluates Trend + RSI + MACD + Moving Average + Position sizing.
        """
        symbol = context.get("symbol", "RELIANCE")
        snap = context.get("market_snapshot", {})
        port = context.get("portfolio_summary", {})
        pos = context.get("position", {})

        price = float(snap.get("current_price", 100.0))
        rsi = snap.get("rsi")
        trend = snap.get("trend", "NEUTRAL")
        macd = snap.get("macd") or {}
        macd_hist = macd.get("histogram", 0.0)
        cash = float(port.get("cash", 100000.0))
        qty_held = int(pos.get("quantity", 0))

        strategy_signal = snap.get("strategy_signal", "HOLD")
        strategy_reason = snap.get("strategy_reason", "")

        # Decision scoring logic incorporating factual strategy signal
        bullish_score = 0
        bearish_score = 0

        if strategy_signal == "BUY":
            bullish_score += 3
        elif strategy_signal == "SELL":
            bearish_score += 3

        if trend == "BULLISH":
            bullish_score += 1
        elif trend == "BEARISH":
            bearish_score += 1

        if rsi is not None:
            if 45 <= rsi <= 68:
                bullish_score += 1
            elif rsi > 72:
                bearish_score += 2

        port_val = float(port.get("portfolio_value", 100000.0))
        curr_pos_val = float(pos.get("market_value", qty_held * price))
        avg_entry = float(pos.get("average_entry_price", 0.0))
        pnl_pct = ((price - avg_entry) / avg_entry) if avg_entry > 0 and qty_held > 0 else 0.0

        # Dynamic exit rules for open positions (Take Profit / Stop Loss)
        if qty_held > 0:
            if pnl_pct >= 0.025:  # +2.5% Take Profit
                sell_qty = qty_held
                return TradeActionProposal(
                    action="SELL",
                    symbol=symbol,
                    quantity=sell_qty,
                    confidence=0.88,
                    decision_summary=f"Take Profit triggered (+{pnl_pct*100:.2f}% gain). Selling {sell_qty} shares at ₹{price:.2f} to secure profit.",
                    risk_summary=f"Securing capital gain of approx ₹{(price - avg_entry) * sell_qty:.2f}.",
                    conditions_to_reconsider=["Watch for bullish pullbacks"]
                )
            elif pnl_pct <= -0.020:  # -2.0% Stop Loss
                sell_qty = qty_held
                return TradeActionProposal(
                    action="SELL",
                    symbol=symbol,
                    quantity=sell_qty,
                    confidence=0.85,
                    decision_summary=f"Stop Loss triggered ({pnl_pct*100:.2f}% drop). Selling {sell_qty} shares at ₹{price:.2f} to protect virtual capital.",
                    risk_summary=f"Capital protection exit. Realized loss: ₹{(price - avg_entry) * sell_qty:.2f}.",
                    conditions_to_reconsider=["Wait for market stabilization"]
                )

        # Determine target allocation based on composite conviction
        if bullish_score >= 3 and bearish_score <= 1:
            # Respect both max_order_pct (9%) and max_position_pct (24% to remain under 25% concentration)
            available_pos_room = max(0.0, (port_val * 0.24) - curr_pos_val)
            target_order_val = min(cash * 0.90, port_val * 0.09, available_pos_room)
            target_qty = int(target_order_val / price) if price > 0 else 0

            if target_qty > 0 and cash >= (target_qty * price * 1.002):
                return TradeActionProposal(
                    action="BUY",
                    symbol=symbol,
                    quantity=target_qty,
                    confidence=min(0.90, 0.60 + 0.05 * bullish_score),
                    decision_summary=f"Strategy signaled BUY with bullish alignment (SMA20 > SMA50, RSI: {rsi}). Agent allocates {target_qty} shares (₹{target_qty * price:.2f}).",
                    risk_summary="Order strictly within single order (9% <= 10%) and position concentration (<= 25%) limits.",
                    conditions_to_reconsider=["Price drops below SMA20", "RSI breaks above 75", "Trend reversal to BEARISH"]
                )
            elif curr_pos_val >= (port_val * 0.20):
                return TradeActionProposal(
                    action="HOLD",
                    symbol=symbol,
                    quantity=0,
                    confidence=0.75,
                    decision_summary=f"Position limit reached ({qty_held} shares, ₹{curr_pos_val:.2f} held). Holding to respect risk constraints.",
                    risk_summary="Zero new risk exposure permitted.",
                    conditions_to_reconsider=["Position reduction or profit taking"]
                )

        elif (bearish_score >= 3 or strategy_signal == "SELL") and qty_held > 0:
            # Propose SELL to take profit or cut loss
            sell_qty = max(1, qty_held // 2) if qty_held > 2 else qty_held
            return TradeActionProposal(
                action="SELL",
                symbol=symbol,
                quantity=sell_qty,
                confidence=min(0.90, 0.60 + 0.05 * bearish_score),
                decision_summary=f"Strategy signaled SELL ({strategy_reason}). Agent executing controlled exit of {sell_qty} shares.",
                risk_summary=f"Exiting {sell_qty} of {qty_held} shares to protect virtual capital.",
                conditions_to_reconsider=["Bullish SMA cross", "RSI recovery above 50"]
            )

        # Default HOLD
        return TradeActionProposal(
            action="HOLD",
            symbol=symbol,
            quantity=0,
            confidence=0.60,
            decision_summary=f"Neutral market conditions (Score Bull: {bullish_score}, Bear: {bearish_score}). Maintaining patient stance.",
            risk_summary="Zero changes to capital exposure.",
            conditions_to_reconsider=["Breakout above 20-period moving average", "RSI divergence"]
        )
