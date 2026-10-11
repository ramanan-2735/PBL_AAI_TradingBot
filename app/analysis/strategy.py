from typing import Dict, Any, Optional
from app.analysis.indicators import TechnicalIndicators
from app.data.models import MarketCandle

class SimpleExplainableStrategy:
    """Deterministic, factual market signal generator.
    STRATEGY != AGENT.
    This module only evaluates market rules and produces a factual setup signal.
    The LangGraph Autonomous Agent receives this signal as an input, reasons about it
    alongside portfolio exposure, volatility, and memory, and decides whether to act.
    
    Rules:
    - BUY Setup: SMA20 > SMA50 AND Price > SMA20 AND 45 <= RSI <= 70
    - SELL Setup: SMA20 < SMA50 OR Price < SMA20 OR RSI > 75
    - HOLD: Otherwise
    """

    @staticmethod
    def evaluate(
        current_candle: MarketCandle,
        sma_20: Optional[float],
        sma_50: Optional[float],
        rsi: Optional[float]
    ) -> Dict[str, Any]:
        price = current_candle.close

        if sma_20 is None or sma_50 is None or rsi is None:
            return {
                "signal": "HOLD",
                "reason": "Insufficient historical data for SMA20/SMA50/RSI calculations.",
                "setup_confidence": 0.0
            }

        # BUY Setup
        if (sma_20 > sma_50) and (price > sma_20) and (45.0 <= rsi <= 70.0):
            return {
                "signal": "BUY",
                "reason": f"Bullish momentum: SMA20 (₹{sma_20:.2f}) > SMA50 (₹{sma_50:.2f}), Price (₹{price:.2f}) > SMA20, and RSI ({rsi:.1f}) in healthy expansion zone [45-70].",
                "setup_confidence": 0.80
            }

        # SELL Setup
        if (sma_20 < sma_50) or (price < sma_20) or (rsi > 75.0):
            reasons = []
            if sma_20 < sma_50:
                reasons.append("SMA20 crossed below SMA50 (Death Cross structure)")
            if price < sma_20:
                reasons.append("Price fell below 20-period moving average")
            if rsi > 75.0:
                reasons.append("RSI in extreme overbought territory (> 75)")
            return {
                "signal": "SELL",
                "reason": "Bearish or exhaustion trigger: " + ", ".join(reasons) + ".",
                "setup_confidence": 0.75
            }

        # Default Neutral
        return {
            "signal": "HOLD",
            "reason": f"No directional setup: Price ₹{price:.2f}, SMA20 ₹{sma_20:.2f}, SMA50 ₹{sma_50:.2f}, RSI {rsi:.1f}. Market is consolidating.",
            "setup_confidence": 0.50
        }
