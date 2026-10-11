from datetime import datetime
from typing import List, Optional, Callable
from app.data.models import MarketCandle, MarketTick
from app.data.providers.base import MarketDataProvider
from app.data.normalizer import MarketDataNormalizer

class ReplayMarketDataProvider(MarketDataProvider):
    """Provides historical candles strictly sequentially to guarantee zero look-ahead bias."""

    def __init__(self, candles: List[MarketCandle]):
        self.candles = MarketDataNormalizer.deduplicate_and_sort(candles)
        self.cursor = 0

    def get_historical_candles(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1m"
    ) -> List[MarketCandle]:
        filtered = [
            c for c in self.candles 
            if c.symbol == symbol and start_date <= c.timestamp <= end_date
        ]
        return filtered

    def get_latest_quote(self, symbol: str) -> Optional[MarketTick]:
        if 0 <= self.cursor < len(self.candles):
            curr = self.candles[self.cursor]
            return MarketTick(
                symbol=curr.symbol,
                timestamp=curr.timestamp,
                last_price=curr.close,
                volume=curr.volume
            )
        return None

    def has_next(self) -> bool:
        return self.cursor < len(self.candles)

    def next_candle(self) -> Optional[MarketCandle]:
        if self.cursor < len(self.candles):
            candle = self.candles[self.cursor]
            self.cursor += 1
            return candle
        return None

    def reset(self):
        self.cursor = 0

    def subscribe_live(self, symbols: List[str], on_tick: Callable[[MarketTick], None]) -> None:
        pass

    def unsubscribe(self) -> None:
        pass
