import pytest
import math
from app.analysis.indicators import TechnicalIndicators
from app.data.models import MarketCandle
from datetime import datetime

def test_sma_calculation():
    prices = [10.0, 20.0, 30.0, 40.0, 50.0]
    sma = TechnicalIndicators.calculate_sma(prices, period=5)
    assert sma == 30.0
    # Insufficient elements returns None
    assert TechnicalIndicators.calculate_sma(prices, period=10) is None

def test_ema_calculation():
    prices = [10.0] * 20 + [20.0] * 5
    ema = TechnicalIndicators.calculate_ema(prices, period=20)
    assert ema is not None
    assert 10.0 < ema < 20.0

def test_rsi_bounds_and_oversold_overbought():
    # Downward trending prices -> RSI should be low (oversold)
    down_prices = [100.0 - i * 2.0 for i in range(25)]
    rsi_down = TechnicalIndicators.calculate_rsi(down_prices, period=14)
    assert rsi_down is not None
    assert 0.0 <= rsi_down <= 30.0

    # Upward trending prices -> RSI should be high (overbought)
    up_prices = [100.0 + i * 2.0 for i in range(25)]
    rsi_up = TechnicalIndicators.calculate_rsi(up_prices, period=14)
    assert rsi_up is not None
    assert 70.0 <= rsi_up <= 100.0

def test_macd_calculation():
    prices = [100.0 + math.sin(i / 5.0) * 10.0 for i in range(60)]
    macd = TechnicalIndicators.calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)
    assert macd is not None
    assert "macd" in macd
    assert "signal" in macd
    assert "histogram" in macd
    assert isinstance(macd["histogram"], float)
