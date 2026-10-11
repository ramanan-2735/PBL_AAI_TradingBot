from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Callable
from app.data.models import MarketCandle, MarketTick

class MarketDataProvider(ABC):
    """Abstract Market Data Provider interface ensuring zero coupling between core agents and data sources."""

    @abstractmethod
    def get_historical_candles(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1m"
    ) -> List[MarketCandle]:
        """Fetch historical candles in chronological order."""
        pass

    @abstractmethod
    def get_latest_quote(self, symbol: str) -> Optional[MarketTick]:
        """Fetch current market price and tick information."""
        pass

    @abstractmethod
    def subscribe_live(self, symbols: List[str], on_tick: Callable[[MarketTick], None]) -> None:
        """Subscribe to live ticks."""
        pass

    @abstractmethod
    def unsubscribe(self) -> None:
        """Unsubscribe and close connections."""
        pass
