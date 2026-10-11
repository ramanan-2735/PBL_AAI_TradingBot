import math
from typing import List, Optional, Tuple, Dict
from app.data.models import MarketCandle

class TechnicalIndicators:
    """Deterministic quantitative indicators implemented from first principles.
    Operates strictly on the provided historical candle series with ZERO look-ahead bias.
    """

    @staticmethod
    def calculate_sma(prices: List[float], period: int = 20) -> Optional[float]:
        """Simple Moving Average (SMA)."""
        if len(prices) < period or period <= 0:
            return None
        return sum(prices[-period:]) / float(period)

    @staticmethod
    def calculate_ema(prices: List[float], period: int = 20) -> Optional[float]:
        """Exponential Moving Average (EMA)."""
        if len(prices) < period or period <= 0:
            return None
        multiplier = 2.0 / (period + 1.0)
        # Seed EMA with initial SMA of the first `period` elements
        ema = sum(prices[:period]) / float(period)
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        return ema

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """Relative Strength Index (RSI) using Wilder's smoothing method."""
        if len(prices) < period + 1 or period <= 0:
            return None

        gains = []
        losses = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(change))

        # Initial averages
        avg_gain = sum(gains[:period]) / float(period)
        avg_loss = sum(losses[:period]) / float(period)

        # Smoothed averages
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / float(period)
            avg_loss = (avg_loss * (period - 1) + losses[i]) / float(period)

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return round(rsi, 2)

    @staticmethod
    def calculate_macd(
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Optional[Dict[str, float]]:
        """Moving Average Convergence Divergence (MACD)."""
        if len(prices) < slow_period + signal_period:
            return None

        # Build MACD line series across historical window
        macd_series = []
        k_fast = 2.0 / (fast_period + 1.0)
        k_slow = 2.0 / (slow_period + 1.0)

        ema_fast = sum(prices[:fast_period]) / float(fast_period)
        for p in prices[fast_period:]:
            ema_fast = (p - ema_fast) * k_fast + ema_fast

        # Compute full sequence for slow and fast
        fast_emas = []
        curr_f = sum(prices[:fast_period]) / float(fast_period)
        for i in range(fast_period, len(prices)):
            curr_f = (prices[i] - curr_f) * k_fast + curr_f
            fast_emas.append((i, curr_f))

        slow_emas = []
        curr_s = sum(prices[:slow_period]) / float(slow_period)
        for i in range(slow_period, len(prices)):
            curr_s = (prices[i] - curr_s) * k_slow + curr_s
            slow_emas.append((i, curr_s))

        # Match indices
        slow_dict = dict(slow_emas)
        for idx, f_val in fast_emas:
            if idx in slow_dict:
                macd_series.append(f_val - slow_dict[idx])

        if len(macd_series) < signal_period:
            return None

        macd_line = macd_series[-1]
        # Signal line is EMA of macd_series
        signal_line = TechnicalIndicators.calculate_ema(macd_series, signal_period)
        if signal_line is None:
            return None

        histogram = macd_line - signal_line
        return {
            "macd": round(macd_line, 2),
            "signal": round(signal_line, 2),
            "histogram": round(histogram, 2)
        }

    @staticmethod
    def calculate_volatility(prices: List[float], period: int = 20) -> Optional[float]:
        """Annualized historical volatility from log returns."""
        if len(prices) < period + 1:
            return None

        recent = prices[-(period + 1):]
        returns = [math.log(recent[i] / recent[i - 1]) for i in range(1, len(recent))]
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
        # Annualized assuming 252 trading days * 375 minutes per day = 94,500 1-min candles
        annualized = std_dev * math.sqrt(252)
        return round(annualized, 4)

    @staticmethod
    def calculate_atr(candles: List[MarketCandle], period: int = 14) -> Optional[float]:
        """Average True Range (ATR)."""
        if len(candles) < period + 1:
            return None

        trs = []
        for i in range(1, len(candles)):
            c = candles[i]
            prev_close = candles[i - 1].close
            tr = max(
                c.high - c.low,
                abs(c.high - prev_close),
                abs(c.low - prev_close)
            )
            trs.append(tr)

        atr = sum(trs[:period]) / float(period)
        for i in range(period, len(trs)):
            atr = (atr * (period - 1) + trs[i]) / float(period)
        return round(atr, 2)
