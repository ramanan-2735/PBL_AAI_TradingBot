from typing import List, Dict, Any, Optional
from app.data.models import MarketCandle
from app.analysis.indicators import TechnicalIndicators

class MarketAnalyzer:
    """Combines indicators into an auditable structured market summary for the agent."""

    @staticmethod
    def analyze_window(candles: List[MarketCandle]) -> Dict[str, Any]:
        """Analyzes a window of candles up to the current timestamp.
        Zero look-ahead: candles list MUST only include candles <= current simulation time.
        """
        if not candles:
            return {"error": "No market candles provided"}

        current_candle = candles[-1]
        closes = [c.close for c in candles]
        volumes = [c.volume for c in candles]

        # Calculate indicators
        rsi = TechnicalIndicators.calculate_rsi(closes, period=14)
        sma_20 = TechnicalIndicators.calculate_sma(closes, period=20)
        sma_50 = TechnicalIndicators.calculate_sma(closes, period=50)
        ema_20 = TechnicalIndicators.calculate_ema(closes, period=20)
        macd_info = TechnicalIndicators.calculate_macd(closes, fast_period=12, slow_period=26, signal_period=9)
        volatility = TechnicalIndicators.calculate_volatility(closes, period=20)
        atr = TechnicalIndicators.calculate_atr(candles, period=14)

        # Trend detection
        trend = "NEUTRAL"
        if sma_20 and sma_50:
            if current_candle.close > sma_20 > sma_50:
                trend = "BULLISH"
            elif current_candle.close < sma_20 < sma_50:
                trend = "BEARISH"

        # Volume condition
        volume_status = "NORMAL"
        if len(volumes) >= 20:
            avg_vol = sum(volumes[-20:]) / 20.0
            if current_candle.volume > avg_vol * 1.5:
                volume_status = "HIGH"
            elif current_candle.volume < avg_vol * 0.6:
                volume_status = "LOW"

        # Evaluate factual strategy signal
        from app.analysis.strategy import SimpleExplainableStrategy
        strategy_eval = SimpleExplainableStrategy.evaluate(
            current_candle=current_candle,
            sma_20=sma_20,
            sma_50=sma_50,
            rsi=rsi
        )

        return {
            "symbol": current_candle.symbol,
            "timestamp": current_candle.timestamp.isoformat(),
            "current_price": current_candle.close,
            "open": current_candle.open,
            "high": current_candle.high,
            "low": current_candle.low,
            "close": current_candle.close,
            "volume": current_candle.volume,
            "rsi": rsi,
            "sma_20": round(sma_20, 2) if sma_20 else None,
            "sma_50": round(sma_50, 2) if sma_50 else None,
            "ema_20": round(ema_20, 2) if ema_20 else None,
            "macd": macd_info,
            "volatility": volatility,
            "atr": atr,
            "trend": trend,
            "volume_status": volume_status,
            "strategy_signal": strategy_eval["signal"],
            "strategy_reason": strategy_eval["reason"],
            "strategy_confidence": strategy_eval["setup_confidence"],
            "candle_count": len(candles)
        }
