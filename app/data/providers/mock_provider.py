import random
from datetime import datetime, timedelta
from typing import List, Optional, Callable
from app.data.models import MarketCandle, MarketTick
from app.data.providers.base import MarketDataProvider

class MockMarketDataProvider(MarketDataProvider):
    """Provides synthetic deterministic or stochastic market data for development and tests."""

    BASE_PRICES = {
        "RELIANCE": 2850.0,
        "TCS": 3950.0,
        "INFY": 1820.0,
        "HDFCBANK": 1640.0,
        "TATAMOTORS": 980.0
    }

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        self.is_subscribed = False

    def get_historical_candles(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1m"
    ) -> List[MarketCandle]:
        candles = []
        base_price = self.BASE_PRICES.get(symbol.upper(), 1000.0)
        curr_price = base_price
        
        # Step in minutes with realistic NSE trading session (09:15 to 15:30 IST, weekdays only)
        delta = timedelta(minutes=1 if timeframe == "1m" else (5 if timeframe == "5m" else 15))
        curr_ts = start_date.replace(hour=9, minute=15, second=0, microsecond=0)
        
        step = 0
        while curr_ts <= end_date:
            # Skip Saturday (5) and Sunday (6)
            if curr_ts.weekday() >= 5:
                curr_ts = (curr_ts + timedelta(days=1)).replace(hour=9, minute=15)
                continue

            # Skip outside 09:15 - 15:30 trading session
            if curr_ts.hour < 9 or (curr_ts.hour == 9 and curr_ts.minute < 15):
                curr_ts = curr_ts.replace(hour=9, minute=15)
                continue
            if curr_ts.hour > 15 or (curr_ts.hour == 15 and curr_ts.minute > 30):
                curr_ts = (curr_ts + timedelta(days=1)).replace(hour=9, minute=15)
                continue

            cycle = 5.0 * math_sin_approx(step / 15.0)
            noise = (self.rng.random() - 0.49) * 0.008 * curr_price
            curr_price = max(10.0, curr_price + noise + cycle * 0.1)
            
            high = curr_price * (1.0 + self.rng.random() * 0.003)
            low = curr_price * (1.0 - self.rng.random() * 0.003)
            open_p = (curr_price + low) / 2.0
            close_p = curr_price
            vol = round(1000 + self.rng.random() * 5000, 2)
            
            candles.append(MarketCandle(
                symbol=symbol.upper(),
                timestamp=curr_ts,
                open=round(open_p, 2),
                high=round(max(high, open_p, close_p), 2),
                low=round(min(low, open_p, close_p), 2),
                close=round(close_p, 2),
                volume=vol
            ))
            curr_ts += delta
            step += 1

        return candles

    def get_latest_quote(self, symbol: str) -> Optional[MarketTick]:
        base_price = self.BASE_PRICES.get(symbol.upper(), 1000.0)
        noise = (self.rng.random() - 0.5) * 5.0
        price = round(base_price + noise, 2)
        return MarketTick(
            symbol=symbol.upper(),
            timestamp=datetime.now(),
            last_price=price,
            volume=float(self.rng.randint(10, 500)),
            bid_price=round(price - 0.25, 2),
            ask_price=round(price + 0.25, 2)
        )

    def subscribe_live(self, symbols: List[str], on_tick: Callable[[MarketTick], None]) -> None:
        self.is_subscribed = True

    def unsubscribe(self) -> None:
        self.is_subscribed = False

def math_sin_approx(x: float) -> float:
    import math
    return math.sin(x)
