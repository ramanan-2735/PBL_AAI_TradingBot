import math
from datetime import datetime
from typing import List, Optional
from app.data.models import MarketCandle, MarketTick

class MarketDataNormalizer:
    """Cleans, validates, and normalizes raw market records into valid MarketCandle / MarketTick objects."""

    @staticmethod
    def normalize_candle(raw: dict, symbol: str) -> Optional[MarketCandle]:
        try:
            # Handle different key conventions (Open/open/O/etc.)
            ts = raw.get("timestamp") or raw.get("time") or raw.get("datetime")
            if isinstance(ts, (int, float)):
                # epoch timestamp in seconds or milliseconds
                if ts > 1e11:  # ms
                    ts = ts / 1000.0
                ts = datetime.fromtimestamp(ts)
            elif isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

            open_p = float(raw.get("open", raw.get("Open", raw.get("o", 0))))
            high_p = float(raw.get("high", raw.get("High", raw.get("h", 0))))
            low_p = float(raw.get("low", raw.get("Low", raw.get("l", 0))))
            close_p = float(raw.get("close", raw.get("Close", raw.get("c", 0))))
            vol = float(raw.get("volume", raw.get("Volume", raw.get("v", 0))))

            # Sanity checks
            if any(math.isnan(p) or math.isinf(p) or p <= 0 for p in [open_p, high_p, low_p, close_p]):
                return None
            if math.isnan(vol) or vol < 0:
                vol = 0.0

            # Ensure high and low cover open and close
            high_p = max(high_p, open_p, close_p)
            low_p = min(low_p, open_p, close_p)

            candle = MarketCandle(
                symbol=symbol,
                timestamp=ts,
                open=round(open_p, 2),
                high=round(high_p, 2),
                low=round(low_p, 2),
                close=round(close_p, 2),
                volume=round(vol, 2)
            )
            return candle
        except Exception:
            return None

    @staticmethod
    def deduplicate_and_sort(candles: List[MarketCandle]) -> List[MarketCandle]:
        """Removes duplicates and sorts candles chronologically."""
        seen = set()
        deduped = []
        for c in sorted(candles, key=lambda x: x.timestamp):
            if c.timestamp not in seen:
                seen.add(c.timestamp)
                deduped.append(c)
        return deduped
