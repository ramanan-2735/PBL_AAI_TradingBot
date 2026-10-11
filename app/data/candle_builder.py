from datetime import datetime, timedelta
from typing import Optional, Callable
from app.data.models import MarketCandle, MarketTick

class CandleBuilder:
    """Aggregates high-frequency ticks into fixed-interval OHLCV candles (e.g., 1m, 5m)."""

    def __init__(self, symbol: str, interval_seconds: int = 60, on_candle_complete: Optional[Callable[[MarketCandle], None]] = None):
        self.symbol = symbol
        self.interval_seconds = interval_seconds
        self.on_candle_complete = on_candle_complete
        
        self.current_candle_start: Optional[datetime] = None
        self.open: Optional[float] = None
        self.high: Optional[float] = None
        self.low: Optional[float] = None
        self.close: Optional[float] = None
        self.volume: float = 0.0

    def _get_window_start(self, ts: datetime) -> datetime:
        total_seconds = int(ts.timestamp())
        window_sec = total_seconds - (total_seconds % self.interval_seconds)
        return datetime.fromtimestamp(window_sec)

    def process_tick(self, tick: MarketTick) -> Optional[MarketCandle]:
        tick_window = self._get_window_start(tick.timestamp)
        completed_candle = None

        if self.current_candle_start is None:
            self.current_candle_start = tick_window
            self.open = tick.last_price
            self.high = tick.last_price
            self.low = tick.last_price
            self.close = tick.last_price
            self.volume = tick.volume
        elif tick_window > self.current_candle_start:
            # Current candle period completed
            completed_candle = MarketCandle(
                symbol=self.symbol,
                timestamp=self.current_candle_start,
                open=self.open,
                high=self.high,
                low=self.low,
                close=self.close,
                volume=self.volume
            )
            if self.on_candle_complete:
                self.on_candle_complete(completed_candle)

            # Start new candle
            self.current_candle_start = tick_window
            self.open = tick.last_price
            self.high = tick.last_price
            self.low = tick.last_price
            self.close = tick.last_price
            self.volume = tick.volume
        else:
            # Same candle window
            self.high = max(self.high, tick.last_price)
            self.low = min(self.low, tick.last_price)
            self.close = tick.last_price
            self.volume += tick.volume

        return completed_candle
